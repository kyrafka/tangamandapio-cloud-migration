import http from 'k6/http';
import { check, sleep } from 'k6';

const baseUrl = (__ENV.PORTAL_BASE_URL || '').replace(/\/+$/, '');
const portalHost = __ENV.PORTAL_HOST || '';
const originIp = __ENV.ORIGIN_IP || '';
const maxVus = Math.min(3000, Math.max(1, Number(__ENV.TARGET_VUS || 3000)));
const rampUnit = __ENV.RAMP_UNIT || '2m';
const holdDuration = __ENV.HOLD_DURATION || '2m';
const rampDown = __ENV.RAMP_DOWN_DURATION || '20s';
const thinkTimeSeconds = Math.max(1, Number(__ENV.THINK_TIME_SECONDS || 60));
const targets = [
  Math.max(1, Math.floor(maxVus * 0.1)),
  Math.max(1, Math.floor(maxVus * 0.3)),
  Math.max(1, Math.floor(maxVus * 0.6)),
  maxVus,
];

export const options = {
  hosts: { [portalHost || 'localhost']: originIp || '127.0.0.1' },
  scenarios: {
    readiness_with_database_probe: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: rampUnit, target: targets[0] },
        { duration: rampUnit, target: targets[1] },
        { duration: rampUnit, target: targets[2] },
        { duration: rampUnit, target: targets[3] },
        { duration: holdDuration, target: maxVus },
        { duration: rampDown, target: 0 },
      ],
      gracefulRampDown: '15s',
    },
  },
  thresholds: {
    http_req_failed: [{ threshold: 'rate<0.01', abortOnFail: true, delayAbortEval: '30s' }],
    http_req_duration: [{ threshold: 'p(95)<2000' }],
    checks: ['rate>0.99'],
  },
};

export function setup() {
  const urlHost = baseUrl.match(/^https:\/\/([^/:]+)(?::\d+)?$/i);
  if (
    !urlHost ||
    !portalHost ||
    urlHost[1].toLowerCase() !== portalHost.toLowerCase() ||
    !/^\d{1,3}(\.\d{1,3}){3}$/.test(originIp)
  ) {
    throw new Error('Use the verified HTTPS portal URL and one IPv4 address for the ALB origin.');
  }

  const response = http.get(`${baseUrl}/health`, {
    headers: { Accept: 'application/json', 'User-Agent': 'Tangamandapio-Readiness-LoadTest/1.0' },
    timeout: '15s',
    tags: { endpoint: 'setup_readiness' },
  });
  const ready = check(response, {
    'readiness setup is HTTP 200': (res) => res.status === 200,
    'database readiness is ok': (res) => res.json('status') === 'ok',
  });
  if (!ready) {
    throw new Error(`Load test stopped: readiness setup returned HTTP ${response.status}.`);
  }
}

export default function () {
  const response = http.get(`${baseUrl}/health`, {
    headers: { Accept: 'application/json', 'User-Agent': 'Tangamandapio-Readiness-LoadTest/1.0' },
    timeout: '15s',
    tags: { endpoint: 'database_readiness' },
  });
  check(response, {
    'readiness returns HTTP 200': (res) => res.status === 200,
    'database readiness returns ok': (res) => res.json('status') === 'ok',
  });
  sleep(thinkTimeSeconds);
}

// Keep reports safe if this script is reused; no request bodies or cookies are exported.
export function handleSummary(data) {
  const safeReport = { metrics: data.metrics, root_group: data.root_group };
  const outputPath = __ENV.SUMMARY_EXPORT_PATH;
  const outputs = { stdout: JSON.stringify(safeReport.metrics, null, 2) };
  if (outputPath) outputs[outputPath] = JSON.stringify(safeReport, null, 2);
  return outputs;
}
