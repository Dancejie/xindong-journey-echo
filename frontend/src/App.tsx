import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import './styles.css'

type Character = {
  id: string; name: string; mbti: string; tagline: string; accent: string
  portrait: string; video: string; publicMask: string; privateFear: string
  memorySeed: string; voice: string; boundary: string; quickPrompts: string[]
  independentInterest: string; eventLabel: string
}

type Memory = {
  id: string; characterId: string; playerText: string; agentReply: string
  intentId: string; affectionDelta: number; trustDelta: number; createdAt: string
  attitude: string; stageDirection?: string; summary?: string
  relationshipDelta: Record<string, number>
}

type RelationshipAxes = { trust: number; affection: number; respect: number; fear: number; debt: number; attraction: number; resentment: number }
type StoryEvent = { eventId: string; characterId: string; label: string; text: string }

type Snapshot = {
  runId: string; revision: number; nodeId: string
  player: { mbti: string; displayName: string }
  flags: { heat: number; clarity: number; publicImpression: number }
  affection: Record<string, number>; trust: Record<string, number>
  relationships: Record<string, RelationshipAxes>; attitudes: Record<string, string>
  eventLedger: StoryEvent[]; activeEventId: string | null
  focusCharacterId: string | null; letterRecipientId: string | null
  echoMemories: Memory[]; choiceHistory: unknown[]
}

type Choice = { id: string; label: string; hint: string; characterId?: string }
type StoryNode = {
  chapter: string; eyebrow: string; title: string; speaker: string; text: string
  characterId?: string; cinematic?: string; choices: Choice[]
  requiresMemory?: boolean; requiresEvent?: boolean; characterChoice?: boolean; isEnding?: boolean
}
type View = { snapshot: Snapshot; node: StoryNode; characters: Character[] }
type Receipt = { kind: string; intentId?: string; attitude?: string; publicReason?: string; patch?: Record<string, unknown>; eventActivation?: StoryEvent | null }

const MBTIS = ['INFP', 'ENFP', 'INFJ', 'ENFJ', 'INTJ', 'ENTJ', 'INTP', 'ENTP', 'ISFP', 'ESFP', 'ISFJ', 'ESFJ', 'ISTP', 'ESTP', 'ISTJ', 'ESTJ']
const PROGRESS: Record<string, number> = { arrival: 8, 'first-look': 26, 'private-window': 48, 'event-reveal': 68, 'anonymous-letter': 84, callback: 100 }
const ATTITUDE_LABELS: Record<string, string> = { warm: '温暖', curious: '好奇', guarded: '戒备', challenging: '试探', vulnerable: '袒露', softened: '松动', uncertain: '迟疑', honest: '坦诚', moved: '被触动', careful: '谨慎', steady: '稳定', boundary: '边界' }
const AXIS_LABELS: Record<string, string> = { trust: '信任', affection: '好感', respect: '尊重', fear: '压力', debt: '亏欠', attraction: '吸引', resentment: '芥蒂' }

function getClientId() {
  const key = 'heart-journey-public-client-id'
  try {
    const saved = localStorage.getItem(key)
    if (saved) return saved
    const created = globalThis.crypto?.randomUUID?.() || `guest-${Date.now()}-${Math.random().toString(36).slice(2)}`
    localStorage.setItem(key, created)
    return created
  } catch {
    return `guest-${Date.now()}-${Math.random().toString(36).slice(2)}`
  }
}

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'X-Client-Id': getClientId(), ...(options?.headers || {}) },
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.detail || '心动信号暂时中断，请稍后重试')
  return payload
}

function MediaVideo({ src, className = '', poster, onError }: { src: string; className?: string; poster?: string; onError?: () => void }) {
  return <video className={className} src={src} poster={poster} autoPlay muted loop playsInline preload="metadata" onError={onError} />
}

function HeartMark({ small = false }: { small?: boolean }) {
  return <span className={small ? 'heart-mark heart-mark--small' : 'heart-mark'} aria-hidden="true">♡</span>
}

function Loading() {
  return <main className="loading-screen"><div className="loading-orbit"><HeartMark /></div><p>正在接入心动小屋…</p></main>
}

function LoginGate({ message }: { message: string }) {
  return (
    <main className="login-gate">
      <div className="login-card glass-card">
        <span className="kicker">HEART JOURNEY · INTERNAL PREVIEW</span>
        <HeartMark />
        <h1>需要内网身份</h1>
        <p>{message}</p>
        <button className="primary-button" onClick={() => location.reload()}>重新进入</button>
      </div>
    </main>
  )
}

function Landing({ characters, onStart, busy }: { characters: Character[]; onStart: (mbti: string) => void; busy: boolean }) {
  const [mbti, setMbti] = useState('INFP')
  const [mediaFailed, setMediaFailed] = useState(false)
  return (
    <main className="landing">
      <div className="landing-media" aria-hidden="true">
        {!mediaFailed && <MediaVideo src="/media/video/E01-arrival-reveal.mp4" onError={() => setMediaFailed(true)} />}
        <div className="landing-scrim" />
        <div className="sun-glow" />
      </div>
      <header className="landing-topbar">
        <span>全球首档 MBTI 沉浸式恋爱实验</span>
        <span className="live-pill"><i /> DAY 1</span>
      </header>
      <section className="landing-copy">
        <p className="landing-overline">选择一种靠近的方式</p>
        <div className="title-lockup">
          <h1>心动之旅</h1><HeartMark />
          <p>MBTI 恋爱模拟器</p>
        </div>
        <p className="landing-manifesto">没有人是被“拯救”的。<br />每个人都带着自己的软处走进来。</p>
      </section>
      <section className="cast-ribbon" aria-label="本季嘉宾">
        {characters.map((character) => (
          <article className="cast-mini" key={character.id} style={{ '--accent': character.accent } as React.CSSProperties}>
            <div className="cast-mini__image"><img src={character.portrait} alt={character.name} /></div>
            <b>{character.mbti}</b><span>{character.name}</span>
          </article>
        ))}
      </section>
      <section className="start-panel glass-card">
        <div className="start-panel__heading"><span>你的观察视角</span><small>不是标签，只是故事的起点</small></div>
        <div className="mbti-picker" role="listbox" aria-label="选择 MBTI">
          {MBTIS.map((item) => <button key={item} className={item === mbti ? 'active' : ''} onClick={() => setMbti(item)}>{item}</button>)}
        </div>
        <button className="primary-button start-button" disabled={busy} onClick={() => onStart(mbti)}>
          <span>{busy ? '正在开启…' : '以我的方式进入小屋'}</span><i>→</i>
        </button>
        <p className="privacy-note">你的选择会改变剧情，也会成为每位嘉宾独立记忆的一部分</p>
      </section>
    </main>
  )
}

function CharacterDock({ characters, snapshot, onOpen }: { characters: Character[]; snapshot: Snapshot; onOpen: (character: Character) => void }) {
  return (
    <nav className="character-dock" aria-label="1 对 1 心动私聊">
      <div className="dock-label"><span>心动小屋</span><small>点击进入 1 对 1</small></div>
      <div className="dock-scroll">
        {characters.map((character) => {
          const memoryCount = snapshot.echoMemories.filter(m => m.characterId === character.id).length
          return (
            <button className="dock-avatar" key={character.id} onClick={() => onOpen(character)} style={{ '--accent': character.accent } as React.CSSProperties}>
              <span className="dock-avatar__photo"><img src={character.portrait} alt="" />{memoryCount > 0 && <i>{memoryCount}</i>}</span>
              <b>{character.name}</b><small>{character.mbti}</small>
            </button>
          )
        })}
      </div>
    </nav>
  )
}

function ChatSheet({ character, snapshot, onClose, onSend, busy }: {
  character: Character; snapshot: Snapshot; onClose: () => void
  onSend: (message: string) => Promise<void>; busy: boolean
}) {
  const [draft, setDraft] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const memories = snapshot.echoMemories.filter(memory => memory.characterId === character.id)
  const latest = memories[memories.length - 1]
  const axes = snapshot.relationships?.[character.id]
  const attitude = snapshot.attitudes?.[character.id] || 'curious'
  const submit = async (event?: FormEvent) => {
    event?.preventDefault()
    const message = draft.trim()
    if (!message || busy) return
    setDraft('')
    await onSend(message)
  }
  return (
    <div className="sheet-backdrop" role="dialog" aria-modal="true" aria-label={`与${character.name}私聊`}>
      <section className="chat-sheet" style={{ '--accent': character.accent } as React.CSSProperties}>
        <div className="chat-portrait">
          <div className="chat-portrait__media" aria-hidden="true">
            <MediaVideo className="chat-portrait__blur" src={character.video} poster={character.portrait} />
            <MediaVideo className="chat-portrait__subject" src={character.video} poster={character.portrait} />
          </div>
          <div className="chat-portrait__scrim" />
          <button className="close-button" onClick={onClose} aria-label="关闭私聊">×</button>
          <div className="chat-identity"><span>{character.mbti}</span><h2>{character.name}</h2><p>{character.tagline}</p></div>
          <div className="memory-seal"><HeartMark small /><span>{memories.length ? `${memories.length} 段共同记忆` : '从这一句话开始记住你'}</span></div>
        </div>
        <div className="chat-body">
          <div className="agent-note">
            <span>当前态度 · {ATTITUDE_LABELS[attitude] || attitude}</span>
            <p>{character.independentInterest}</p>
            {axes && <div className="relationship-axes">
              {(['trust', 'affection', 'respect', 'attraction'] as const).map(axis => <i key={axis}>{AXIS_LABELS[axis]} {axes[axis] >= 0 ? '+' : ''}{axes[axis]}</i>)}
            </div>}
          </div>
          <div className="message-stream">
            {!latest && <div className="message agent"><b>{character.name}</b><p>“这里没有其他人的镜头。你可以不用急着表现得正确。”</p></div>}
            {memories.slice(-4).map(memory => (
              <div className="message-pair" key={memory.id}>
                <div className="message player"><p>{memory.playerText}</p></div>
                <div className="message agent"><b>{character.name} · {ATTITUDE_LABELS[memory.attitude] || memory.attitude}</b>{memory.stageDirection && <em>{memory.stageDirection}</em>}<p>{memory.agentReply}</p><small>{memory.summary || '已写入你们的共同记忆'}</small></div>
              </div>
            ))}
            {busy && <div className="message agent typing"><i /><i /><i /></div>}
          </div>
          <div className="quick-prompts">
            {character.quickPrompts.map(prompt => <button key={prompt} onClick={() => { setDraft(prompt); inputRef.current?.focus() }}>{prompt}</button>)}
          </div>
          <form className="chat-composer" onSubmit={submit}>
            <textarea ref={inputRef} value={draft} maxLength={240} rows={1} placeholder={`只对${character.name}说…`} onChange={e => setDraft(e.target.value)} />
            <button type="submit" disabled={!draft.trim() || busy} aria-label="发送">↗</button>
          </form>
          <p className="memory-rule">这段交流只进入 {character.name} 的记忆；边界与剧情事实由游戏规则裁决</p>
        </div>
      </section>
    </div>
  )
}

function Cinematic({ src, onDone }: { src: string; onDone: () => void }) {
  const [ready, setReady] = useState(false)
  return (
    <div className="cinematic-overlay">
      <video src={src} autoPlay muted playsInline onCanPlay={() => setReady(true)} onEnded={onDone} onError={onDone} />
      <div className="cinematic-grade" />
      <div className={`cinematic-title ${ready ? 'show' : ''}`}><span>HEART JOURNEY</span><b>选择已经发生</b></div>
      <button onClick={onDone}>跳过</button>
    </div>
  )
}

function ReceiptToast({ receipt }: { receipt: Receipt }) {
  const patchCount = Object.keys(receipt.patch || {}).length
  const title = receipt.eventActivation ? `事件激活 · ${receipt.eventActivation.label}` : receipt.kind === 'agent-turn' ? `态度更新 · ${ATTITUDE_LABELS[receipt.attitude || ''] || receipt.attitude}` : '选择已写入故事'
  const detail = receipt.eventActivation?.text || receipt.publicReason || (patchCount ? `${patchCount} 项关系参数已提交` : '剧情状态已提交')
  return <div className="receipt-toast"><HeartMark small /><div><b>{title}</b><span>{detail}</span></div></div>
}

function Game({ view, onView, onRestart }: { view: View; onView: (view: View) => void; onRestart: () => Promise<void> }) {
  const { snapshot, node, characters } = view
  const [chatCharacter, setChatCharacter] = useState<Character | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [receipt, setReceipt] = useState<Receipt | null>(null)
  const [cinematic, setCinematic] = useState<string | null>(node.cinematic || null)
  const activeCharacter = characters.find(c => c.id === node.characterId)
  const sceneMedia = activeCharacter?.video || '/media/video/E01-arrival-reveal.mp4'
  const choose = async (choice: Choice) => {
    setBusy(true); setError('')
    try {
      const result = await api<View & { receipt: Receipt }>(`/api/runs/${snapshot.runId}/choices`, {
        method: 'POST', body: JSON.stringify({ choiceId: choice.id, characterId: choice.characterId, revision: snapshot.revision })
      })
      setReceipt(result.receipt); setTimeout(() => setReceipt(null), 3300)
      onView(result)
      if (result.node.cinematic) setCinematic(result.node.cinematic)
    } catch (reason) { setError((reason as Error).message) }
    finally { setBusy(false) }
  }
  const send = async (message: string) => {
    if (!chatCharacter) return
    setBusy(true); setError('')
    try {
      const result = await api<View & { receipt: Receipt }>(`/api/runs/${snapshot.runId}/agents/${chatCharacter.id}/messages`, {
        method: 'POST', body: JSON.stringify({ message, revision: snapshot.revision })
      })
      setReceipt(result.receipt); setTimeout(() => setReceipt(null), 3300)
      onView(result)
    } catch (reason) { setError((reason as Error).message) }
    finally { setBusy(false) }
  }
  const restart = async () => {
    if (busy) return
    setBusy(true)
    try { await onRestart() }
    finally { setBusy(false) }
  }
  const memoriesDone = snapshot.echoMemories.length > 0
  const eventDone = !!snapshot.activeEventId
  return (
    <main className="game-shell">
      <header className="game-topbar">
        <div><span>心动之旅</span><small>{node.chapter}</small></div>
        <div className="game-progress"><i style={{ width: `${PROGRESS[snapshot.nodeId] || 0}%` }} /></div>
        <button className="signal-button" aria-label="关系状态"><HeartMark small /><span>{snapshot.flags.heat + snapshot.echoMemories.length}</span></button>
      </header>
      <section className="scene-stage">
        <MediaVideo key={sceneMedia} src={sceneMedia} poster={activeCharacter?.portrait} />
        <div className="scene-atmosphere" />
        <div className="scene-time"><span>{node.eyebrow}</span><i /></div>
        {activeCharacter && <div className="scene-character-tag" style={{ '--accent': activeCharacter.accent } as React.CSSProperties}><b>{activeCharacter.name}</b><span>{activeCharacter.mbti} · {activeCharacter.tagline}</span></div>}
      </section>
      <section className="story-card">
        <div className="story-card__chapter"><span>{node.speaker}</span><i /></div>
        <h1>{node.title}</h1>
        <p>{node.text}</p>
        {node.requiresMemory && <div className={`link-proof ${eventDone ? 'done' : ''}`}>
          <span>{eventDone ? '✓' : memoriesDone ? '02' : '01'}</span><div><b>{eventDone ? '专属事件已经进入正片' : memoriesDone ? '继续交流，触发一个具体行动' : '先完成一次 1 对 1 交流'}</b><small>{eventDone ? snapshot.eventLedger[snapshot.eventLedger.length - 1]?.label : memoriesDone ? '角色会依据人物卡决定是否交出线索或邀约' : '点击下方任意嘉宾立绘进入私聊'}</small></div>
        </div>}
        <div className={`choice-stack ${node.characterChoice ? 'character-choices' : ''}`}>
          {node.choices.map((choice, index) => {
            const character = choice.characterId ? characters.find(c => c.id === choice.characterId) : null
            return (
              <button key={choice.id} disabled={busy || (!!node.requiresMemory && !memoriesDone) || (!!node.requiresEvent && !eventDone)} onClick={() => choose(choice)} style={character ? { '--accent': character.accent } as React.CSSProperties : undefined}>
                {character && <img src={character.portrait} alt="" />}
                <span className="choice-index">{String(index + 1).padStart(2, '0')}</span>
                <span className="choice-copy"><b>{choice.label}</b><small>{choice.hint}</small></span><i>→</i>
              </button>
            )
          })}
        </div>
        {node.isEnding && <div className="ending-proof"><span>首个联通闭环已完成</span><p>你的文字选择进入角色记忆，并在剧情回声中触发了新的表达。</p><button disabled={busy} onClick={restart}>{busy ? '正在重启心动信号…' : '重新开始一段旅程'}</button></div>}
        {error && <p className="error-note">{error}</p>}
      </section>
      <CharacterDock characters={characters} snapshot={snapshot} onOpen={setChatCharacter} />
      {chatCharacter && <ChatSheet character={chatCharacter} snapshot={snapshot} onClose={() => setChatCharacter(null)} onSend={send} busy={busy} />}
      {cinematic && <Cinematic src={cinematic} onDone={() => setCinematic(null)} />}
      {receipt && <ReceiptToast receipt={receipt} />}
    </main>
  )
}

export default function App() {
  const [characters, setCharacters] = useState<Character[]>([])
  const [view, setView] = useState<View | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [authError, setAuthError] = useState('')
  useEffect(() => {
    api<{ characters: Character[]; view: View | null }>('/api/bootstrap')
      .then(data => { setCharacters(data.characters); setView(data.view) })
      .catch(error => setAuthError(error.message))
      .finally(() => setLoading(false))
  }, [])
  const cast = useMemo(() => view?.characters || characters, [view, characters])
  const start = async (mbti: string) => {
    setBusy(true)
    try { setView(await api<View>('/api/runs', { method: 'POST', body: JSON.stringify({ mbti }) })) }
    catch (error) { setAuthError((error as Error).message) }
    finally { setBusy(false) }
  }
  if (loading) return <Loading />
  if (authError) return <LoginGate message={authError} />
  if (!view) return <Landing characters={cast} onStart={start} busy={busy} />
  return <Game view={view} onView={setView} onRestart={() => start(view.snapshot.player.mbti)} />
}
