import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

export const analyzeStock = (ticker, market) =>
  http.post('/analyze', { ticker, market }).then(r => r.data)

export const fetchResults = () =>
  http.get('/results').then(r => r.data)

export const fetchResult = (ticker) =>
  http.get(`/results/${ticker}`).then(r => r.data)

export const sendToSlack = (ticker, content, reportFields = null) =>
  http.post('/slack/send', { ticker, content, report_fields: reportFields }).then(r => r.data)

export const discoverStocks = (markets, topN) =>
  http.post('/discover', { markets, top_n: topN }).then(r => r.data)
