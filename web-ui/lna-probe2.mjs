import { chromium } from '@playwright/test'
async function tryIt(label, launchOpts, ctxOpts) {
  try {
    const b = await chromium.launch(launchOpts)
    const ctx = await b.newContext(ctxOpts)
    const p = await ctx.newPage()
    const r = await p.goto('http://192.168.178.101/', { timeout: 8000 })
    console.log(label, '->', r ? r.status() : 'no-response')
    await b.close()
  } catch (e) { console.log(label, '-> ERROR:', e.message.split('\n')[0]) }
}
await tryIt('permission only', {}, { permissions: ['local-network-access'] })
await tryIt('permission + sandbox off + flags',
  { chromiumSandbox: false, args: ['--ip-address-space-overrides=192.168.178.101:80=public','--disable-features=LocalNetworkAccessChecks'] },
  { permissions: ['local-network-access'] })
