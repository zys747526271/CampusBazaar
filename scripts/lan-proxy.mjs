/**
 * 局域网访问用的反向代理（仅本地调试使用，不参与生产部署）。
 *
 * 背景：Windows 防火墙默认拦截外部入站，放行 Python 需要管理员权限；
 * 但本机 Node 已被防火墙放行（rule: node.exe, Inbound/Allow/Public）。
 * 因此由 Node 监听 0.0.0.0:5000，把请求原样转发到 127.0.0.1:5001 的 Flask，
 * 手机在同一 WiFi 下即可访问，无需改防火墙。
 *
 * 用法：
 *   node scripts/lan-proxy.mjs [监听端口] [目标端口]
 * 默认：监听 5000 → 转发 5001。
 */
import http from 'node:http'

const listenPort = Number(process.argv[2] || 5000)
const targetPort = Number(process.argv[3] || 5001)
const targetHost = '127.0.0.1'

const server = http.createServer((req, res) => {
  const headers = { ...req.headers, host: `${targetHost}:${targetPort}` }
  const upstream = http.request(
    { host: targetHost, port: targetPort, method: req.method, path: req.url, headers },
    (upstreamRes) => {
      res.writeHead(upstreamRes.statusCode || 502, upstreamRes.headers)
      upstreamRes.pipe(res)
    }
  )

  upstream.on('error', (error) => {
    if (!res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' })
    }
    res.end(JSON.stringify({ success: false, code: 'PROXY_ERROR', message: `后端未启动或不可达：${error.message}` }))
  })

  req.pipe(upstream)
})

server.listen(listenPort, '0.0.0.0', () => {
  console.log(`[lan-proxy] http://0.0.0.0:${listenPort} -> http://${targetHost}:${targetPort}`)
})
