import { readFile, readdir, stat } from 'node:fs/promises'
import path from 'node:path'
import vm from 'node:vm'
import { fileURLToPath } from 'node:url'

const scriptsDir = path.dirname(fileURLToPath(import.meta.url))
const root = path.dirname(scriptsDir)
const dist = path.resolve(process.argv[2] || path.join(root, 'dist-minitool'))
const allowed = new Set(['.html','.css','.js','.png','.jpg','.jpeg','.gif','.webp','.svg','.woff','.woff2','.json'])
const errors = []
const fail = (message) => errors.push(message)

async function collect(dir) {
  const files=[]
  for (const entry of await readdir(dir,{withFileTypes:true})) {
    const target=path.join(dir,entry.name)
    if(entry.isSymbolicLink()) fail(`symbolic link: ${path.relative(dist,target)}`)
    else if(entry.isDirectory()) files.push(...await collect(target))
    else if(entry.isFile()) files.push(target)
  }
  return files
}
let files=[]
try { files=await collect(dist) } catch(error) { console.error(`Mini Tool validation FAIL\n  ${error.message}`); process.exit(1) }
const relative=files.map((f)=>path.relative(dist,f).split(path.sep).join('/'))
const fileSet=new Set(relative)
const htmlFiles=relative.filter((f)=>path.extname(f).toLowerCase()==='.html')
if(!fileSet.has('index.html')) fail('root index.html is missing')
if(htmlFiles.length!==1||htmlFiles[0]!=='index.html') fail('package must contain exactly one root HTML file')
for(const file of relative){
  if(!allowed.has(path.extname(file).toLowerCase())) fail(`unsupported type: ${file}`)
  if(/(^|\/)(node_modules|\.git|\.codex|\.redInfo)(\/|$)/.test(file)) fail(`forbidden path: ${file}`)
  if(file.endsWith('.map')||file.endsWith('.mp4')||file.endsWith('.py')||file.endsWith('.md')) fail(`development or video artifact: ${file}`)
}
let html=''
try{html=await readFile(path.join(dist,'index.html'),'utf8')}catch{fail('cannot read index.html')}
if(html){
  if(!/^<!DOCTYPE html>/i.test(html.trimStart())) fail('DOCTYPE is missing')
  if(!/<html\b[^>]*lang=["']zh-CN["']/i.test(html)) fail('lang zh-CN is missing')
  if(!/viewport-fit=cover/.test(html)) fail('viewport-fit=cover is missing')
  if(/<base\b|<(?:iframe|object)\b/i.test(html)) fail('base, iframe, object are forbidden')
  if(/\son[a-z]+\s*=/i.test(html)) fail('inline event handler is forbidden')
  if(/\b(?:src|href)=["'](?:https?:|\/\/|\/)/i.test(html)) fail('resource path must be relative')
  const tags=[...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)]
  if(!tags.length) fail('external classic script is missing')
  for(const [,attrs,body] of tags){const src=attrs.match(/\bsrc=["']([^"']+)["']/i)?.[1];if(!src)fail('inline script is forbidden');if(body.trim())fail('script body must be empty');if(/type=["']module["']/i.test(attrs))fail('module script is forbidden');if(src?.startsWith('./')&&!fileSet.has(src.slice(2)))fail(`missing script: ${src}`)}
  for(const match of html.matchAll(/\b(?:src|href)=["']([^"']+)["']/gi)){const ref=match[1];if(ref.startsWith('./')&&!fileSet.has(ref.slice(2)))fail(`missing resource: ${ref}`)}
}
let js='',css=''
for(const file of files){const ext=path.extname(file).toLowerCase();if(ext==='.js'){const source=await readFile(file,'utf8');js+='\n'+source;try{new vm.Script(source,{filename:path.relative(dist,file)})}catch(error){fail(`classic JS syntax: ${error.message}`)}}if(ext==='.css')css+='\n'+await readFile(file,'utf8')}
if(/(^|[;\n}])\s*(?:import\s|export\s)/m.test(js)) fail('module syntax is forbidden')
const banned=[
  ['network request',/\bfetch\s*\(|\bXMLHttpRequest\b/],['socket',/\b(?:WebSocket|EventSource|RTCPeerConnection)\b/],
  ['worker',/\bnew\s+(?:Shared)?Worker\s*\(|serviceWorker\.register/],['dynamic code',/\beval\s*\(|\bnew\s+Function\s*\(|\bWebAssembly\./],
  ['device API',/navigator\.(?:geolocation|clipboard|bluetooth|usb|hid|serial|mediaDevices)\b/],['external window',/\bwindow\.(?:open|prompt)\s*\(/],
  ['external location',/\blocation\.(?:href\s*=|assign\s*\()/]
]
for(const [label,pattern] of banned) if(pattern.test(js)) fail(`forbidden capability: ${label}`)
if(/url\(\s*["']?https?:/i.test(css)||/@import\s+url/i.test(css)) fail('external CSS URL is forbidden')
for(const match of `${html}\n${js}\n${css}`.matchAll(/\.\/assets\/[A-Za-z0-9._\/-]+/g)){const ref=match[0].slice(2);if(!ref.endsWith('/')&&!fileSet.has(ref))fail(`missing referenced asset: ${ref}`)}
const motions=relative.filter((f)=>f.startsWith('assets/media/motion/')&&f.endsWith('.webp'))
if(motions.length!==10) fail(`expected 10 animated WebPs, found ${motions.length}`)
for(const ref of motions){const bytes=await readFile(path.join(dist,ref));if(bytes.subarray(0,4).toString('ascii')!=='RIFF'||bytes.subarray(8,12).toString('ascii')!=='WEBP')fail(`invalid WebP: ${ref}`);if(!bytes.includes(Buffer.from('ANIM'))||!bytes.includes(Buffer.from('ANMF')))fail(`not animated: ${ref}`)}
let total=0
for(const file of files)total+=(await stat(file)).size
if(total>9_000_000)fail(`uncompressed runtime ${total} exceeds user 9 MB target`)
if(errors.length){console.error('Mini Tool validation FAIL');for(const error of [...new Set(errors)])console.error(`  - ${error}`);process.exit(1)}
console.log('Mini Tool validation PASS')
console.log('  root HTML: index.html')
console.log('  external classic scripts: 1')
console.log('  networking / MP4 / forbidden capabilities: 0')
console.log(`  animated WebP: ${motions.length}/10`)
console.log(`  files: ${files.length}`)
console.log(`  uncompressed: ${(total/1024/1024).toFixed(2)} MiB`)
