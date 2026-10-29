import http from 'k6/http';
import { check, sleep } from 'k6';

const baseUrl = (__ENV.PORTAL_BASE_URL || '').replace(/\/+$/, '');
const portalHost = __ENV.PORTAL_HOST || '';
const originIp = __ENV.ORIGIN_IP || '';
const path = __ENV.TARGET_PATH || '/';
const maxVus = Math.min(3000, Math.max(1, Number(__ENV.TARGET_VUS || 120)));
const rampUnit = __ENV.RAMP_UNIT || '20s';
const holdDuration = __ENV.HOLD_DURATION || '120s';
const rampDown = __ENV.RAMP_DOWN_DURATION || '20s';
const thinkTimeSeconds = Math.max(1, Number(__ENV.THINK_TIME_SECONDS || 1));
const targets = [
  Math.max(1, Math.floor(maxVus * 0.1)),
  Math.max(1, Math.floor(maxVus * 0.3)),
  Math.max(1, Math.floor(maxVus * 0.6)),
  maxVus,
];

export const options = {
  hosts: { [portalHost || 'localhost']: originIp || '127.0.0.1' },
  scenarios: {
    alb_request_scale_out: {
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
    !/^\d{1,3}(\.\d{1,3}){3}$/.test(originIp) ||
    !path.startsWith('/') ||
    path.startsWith('//')
  ) {
    throw new Error('Use the verified HTTPS portal URL, its ALB origin IPv4, and a same-origin path.');
  }

  const response = http.get(`${baseUrl}${path}`, {
    headers: { Accept: 'text/html,application/json', 'User-Agent': 'Tangamandapio-ALB-ScaleTest/1.0' },
    timeout: '15s',
    tags: { endpoint: 'setup_alb_request_scale' },
  });
  if (!check(response, { 'setup endpoint is HTTP 200': (res) => res.status === 200 })) {
    throw new Error(`Scale test stopped: setup endpoint returned HTTP ${response.status}.`);
  }
}

export default function () {
  const response = http.get(`${baseUrl}${path}`, {
    headers: { Accept: 'text/html,application/json', 'User-Agent': 'Tangamandapio-ALB-ScaleTest/1.0' },
    timeout: '15s',
    tags: { endpoint: 'alb_request_scale' },
  });
  check(response, { 'portal endpoint returns HTTP 200': (res) => res.status === 200 });
  sleep(thinkTimeSeconds);
}

export function handleSummary(data) {
  const safeReport = { metrics: data.metrics, root_group: data.root_group };
  const outputPath = __ENV.SUMMARY_EXPORT_PATH;
  const outputs = { stdout: JSON.stringify(safeReport.metrics, null, 2) };
  if (outputPath) outputs[outputPath] = JSON.stringify(safeReport, null, 2);
  return outputs;
}
