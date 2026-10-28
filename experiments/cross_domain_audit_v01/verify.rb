# Independent arithmetic check from raw API bodies (does not load Python helpers).
require 'json'
require 'zlib'
require 'date'
require 'digest'

snapshot, analysis, receipt_path = ARGV
abort 'usage: ruby verify.rb SNAPSHOT ANALYSIS' unless snapshot && analysis
summary = JSON.parse(File.read(File.join(analysis, 'summary.json')))
manifest = JSON.parse(File.read(File.join(snapshot, 'manifest.json')))
data = {}
manifest.fetch('sources').each do |s|
  path = File.join(snapshot, s.fetch('file'))
  raw = Zlib::GzipReader.open(path, &:read)
  abort 'raw hash mismatch' unless Digest::SHA256.hexdigest(raw) == s.fetch('raw_sha256')
  data[s.fetch('file')] = JSON.parse(raw)
end
rows = data.select { |k, _| k.start_with?('fema_page_') }.values.flat_map { |d| d.fetch('DisasterDeclarationsSummaries') }
groups = rows.group_by { |r| r.fetch('femaDeclarationString') }
records = groups.values.map(&:first)
checks = 0

def difference(row, a, b)
  return nil if row[a].nil? || row[b].nil?
  (Date.iso8601(row[b][0, 10]) - Date.iso8601(row[a][0, 10])).to_i
end

def check_distribution(values, expected)
  observed = values.compact.sort
  actual = {'n_total' => values.size, 'n_observed' => observed.size,
            'n_missing' => values.size - observed.size,
            'n_negative' => observed.count { |v| v < 0 }, 'n_zero' => observed.count(0),
            'min' => observed.first, 'max' => observed.last}
  {'q25' => 0.25, 'median' => 0.5, 'q75' => 0.75, 'q90' => 0.9}.each do |k, p|
    if observed.empty?
      actual[k] = nil
    else
      position = p * (observed.size - 1)
      index, fraction = position.divmod(1)
      actual[k] = observed[index] * (1 - fraction) + observed[[index + 1, observed.size - 1].min] * fraction
    end
  end
  actual.each do |k, v|
    right = expected.fetch(k)
    abort "distribution mismatch #{k}: #{v} != #{right}" unless v == right || (v && right && (v - right).abs < 1e-9)
  end
  actual.size
end

abort 'FEMA row/grain mismatch' unless rows.size == summary['fema']['raw_area_rows'] && records.size == summary['fema']['declarations']
intervals = {
  'begin_to_declaration_days' => ['incidentBeginDate', 'declarationDate'],
  'begin_to_request_days' => ['incidentBeginDate', 'declarationRequestDate'],
  'request_to_declaration_days' => ['declarationRequestDate', 'declarationDate']
}
summary['fema']['summaries'].each do |s|
  selected = records.select do |r|
    s['dimension'] == 'all' || (s['dimension'] == 'year' ? r['declarationDate'][0, 4].to_i : r[s['dimension']]) == s['group']
  end
  intervals.each { |name, (a, b)| checks += check_distribution(selected.map { |r| difference(r, a, b) }, s[name]) }
end
checks += check_distribution(rows.map { |r| difference(r, 'incidentBeginDate', 'declarationDate') }, summary['fema']['raw_area_weighted_begin_to_declaration'])
summary['world_bank']['window_summaries'].each do |s|
  values = data.fetch('wb_data_' + s.fetch('indicator') + '.json.gz')[1].select do |r|
    r['countryiso3code'] == s['country'] && (s['start']..s['end']).cover?(r['date'].to_i)
  end.map { |r| r['value'] }.compact
  abort 'WB denominator mismatch' unless values.size == s['n_observed']
  mean = values.sum.to_f / values.size
  abort 'WB mean mismatch' unless (mean - s['mean_annual_ratio_pct']).abs < 1e-10
  checks += 2
end
result = {'result' => 'PASS', 'independent_value_checks' => checks,
                           'source' => 'raw API JSON, Ruby Date/Array arithmetic',
                           'fema_declarations' => records.size,
                           'verify_sha256' => Digest::SHA256.file(__FILE__).hexdigest,
                           'summary_sha256' => Digest::SHA256.file(File.join(analysis, 'summary.json')).hexdigest,
                           'snapshot_manifest_sha256' => Digest::SHA256.file(File.join(snapshot, 'manifest.json')).hexdigest,
                           'does_not_validate' => ['source date correctness', 'causality', 'payment or protection outcomes']}
if receipt_path
  File.open(receipt_path, File::WRONLY | File::CREAT | File::EXCL) { |f| f.write(JSON.pretty_generate(result) + "\n") }
end
puts JSON.pretty_generate(result)
