import { sleep } from 'k6'
import http from 'k6/http'

const aws_lb_dns_name = __ENV.AWS_COMMUNITY_DAY_LB_DNS_NAME
const api_endpoint = __ENV.AWS_COMMUNITY_DAY_API_ENDPOINT
const api_endpoint_param = __ENV.AWS_COMMUNITY_DAY_API_ENDPOINT_PARAM

const scenarios = {
  Scenario_1: {
    executor: 'ramping-vus',
    gracefulStop: '30s',
    stages: [
      { target: 20, duration: '4m' },
      { target: 20, duration: '6m' },
      { target: 0, duration: '2m' },
    ],
    gracefulRampDown: '30s',
    exec: 'scenario',
  },
  Scenario_2: {
    executor: 'ramping-vus',
    gracefulStop: '30s',
    stages: [
      { target: 20, duration: '1m' },
      { target: 20, duration: '3m' },
      { target: 0, duration: '2m' },
    ],
    gracefulRampDown: '30s',
    exec: 'scenario',
  },
};

const { SCENARIO } = __ENV;
export const options = {
  thresholds: {},
  scenarios: SCENARIO ? {
    [SCENARIO]: scenarios[SCENARIO]
  } : {},
}

export function scenario() {
  let response

  // Cpu intensive
  response = http.get(
    `http://${aws_lb_dns_name}:8000/${api_endpoint}?${api_endpoint_param}`
  )

  // Automatically added sleep
  sleep(1)
}
