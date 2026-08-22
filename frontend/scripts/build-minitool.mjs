import { cp, mkdir, readdir, rm, stat } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptsDir = path.dirname(fileURLToPath(import.meta.url))
const root = path.dirname(scriptsDir)
const source = path.join(root, 'minitool-src')
const dist = path.join(root, 'dist-minitool')
const portraits = path.join(root, 'public', 'media', 'portraits')

await rm(dist, { recursive: true, force: true })
await mkdir(dist, { recursive: true })
await cp(path.join(source, 'index.html'), path.join(dist, 'index.html'))
await cp(path.join(source, 'assets'), path.join(dist, 'assets'), {
  recursive: true,
  filter: (item) => !item.endsWith('.DS_Store'),
})
await mkdir(path.join(dist, 'assets', 'media', 'portraits'), { recursive: true })
await cp(portraits, path.join(dist, 'assets', 'media', 'portraits'), {
  recursive: true,
  filter: (item) => !item.endsWith('.DS_Store'),
})

async function collect(dir) {
  const files = []
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const target = path.join(dir, entry.name)
    if (entry.isDirectory()) files.push(...await collect(target))
    else if (entry.isFile()) files.push(target)
  }
  return files
}
const files = await collect(dist)
let bytes = 0
for (const file of files) bytes += (await stat(file)).size
console.log(`Mini Tool runtime built: ${files.length} files, ${(bytes/1024/1024).toFixed(2)} MiB`)
