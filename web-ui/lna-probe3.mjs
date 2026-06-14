import { chromium } from '@playwright/test'
try {
  const b = await chromium.launch({ chromiumSandbox: false, args: ['--ip-address-space-overrides=192.168.178.101:80=public','--disable-features=LocalNetworkAccessChecks'] })
  const ctx = await b.newContext({ permissions: ['local-network-access'] })
  const p = await ctx.newPage()
  const r = await p.goto('http://192.168.178.101/', { timeout: 8000 })
  console.log('RESULT:', r ? r.status() : 'no-response')
  await b.close()
} catch (e) { console.log('RESULT ERROR:', e.message.split('\n')[0]) }
