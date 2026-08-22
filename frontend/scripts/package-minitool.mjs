import { createHash } from 'node:crypto'
import { mkdir, readFile, rm, stat } from 'node:fs/promises'
import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptsDir=path.dirname(fileURLToPath(import.meta.url))
const root=path.dirname(scriptsDir)
const project=path.dirname(root)
const dist=path.join(root,'dist-minitool')
const release=path.join(project,'release')
const zipPath=path.join(release,'xindong-journey-minitool-1.4.1.zip')
const run=(script)=>{const result=spawnSync(process.execPath,[path.join(scriptsDir,script)],{cwd:root,stdio:'inherit'});if(result.error)throw result.error;if(result.status!==0)process.exit(result.status||1)}
await mkdir(release,{recursive:true})
await rm(zipPath,{force:true})
run('build-minitool.mjs')
run('validate-minitool.mjs')
const zipped=spawnSync('zip',['-X','-q','-r',zipPath,'.','-x','*.DS_Store'],{cwd:dist,stdio:'inherit'})
if(zipped.error)throw zipped.error
if(zipped.status!==0)process.exit(zipped.status||1)
const listed=spawnSync('unzip',['-Z1',zipPath],{encoding:'utf8'})
if(listed.status!==0)process.exit(listed.status||1)
const entries=listed.stdout.split(/\r?\n/).filter(Boolean)
if(!entries.includes('index.html')||entries.some((entry)=>entry!== 'index.html'&&entry.endsWith('/index.html')))throw new Error('ZIP root is invalid')
if(entries.some((entry)=>entry.startsWith('/')||entry.includes('../')))throw new Error('unsafe ZIP entry')
const bytes=(await stat(zipPath)).size
if(bytes>9_000_000){await rm(zipPath,{force:true});throw new Error(`ZIP ${bytes} exceeds 9 MB target`)}
const hash=createHash('sha256').update(await readFile(zipPath)).digest('hex')
console.log('\nMini Tool package PASS')
console.log(`  artifact: ${zipPath}`)
console.log(`  entries: ${entries.length}`)
console.log(`  compressed: ${bytes.toLocaleString()} bytes / 9,000,000`)
console.log(`  sha256: ${hash}`)
