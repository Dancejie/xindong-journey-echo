import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import './styles.css'

type Character = {
  id: string; name: string; mbti: string; tagline: string; accent: string
  portrait: string; video: string; publicMask: string; privateFear: string
  memorySeed: string; voice: string; boundary: string; quickPrompts: string[]
  independentInterest: string; eventLabel: string
  opener?: ChatOpener | string; openingLine?: string; suggestedPrompts?: ChatSuggestionInput[]
  isPlayerPerspective?: boolean; chatEnabled?: boolean; isGuidedTarget?: boolean
}

type Memory = {
  id: string; characterId: string; playerText: string; agentReply: string
  intentId: string; affectionDelta: number; trustDelta: number; createdAt: string
  attitude: string; stageDirection?: string; summary?: string
  relationshipDelta: Record<string, number>
  suggestions?: ChatSuggestionInput[]; suggestedPrompts?: ChatSuggestionInput[]
  suggestionsSource?: 'deepseek' | 'engine-fallback' | string
}

type RelationshipAxes = { trust: number; affection: number; respect: number; fear: number; debt: number; attraction: number; resentment: number }
type StoryEvent = { eventId: string; characterId: string; label: string; text: string }
type StoryMission = {
  id: string; eventId: string; title: string; bridgeText: string; prompt: string
  objective: string; deadline: string; successEvidence: string; exit: string
  sceneSetup?: string; reversalBeat?: string; characterInsight?: string; visualCue?: string; availableStrategies?: string[]
  participantIds: string[]; urgency: 'low' | 'medium' | 'high'; status: 'active'
  media?: {
    assetId?: string; src?: string; poster?: string; durationSeconds?: number
    available?: boolean; status?: 'ready' | 'planned' | string
    fallback?: { kind?: string; src?: string; poster?: string }
  }
}

type PendingChat = boolean | string | {
  id?: string; characterId?: string; targetCharacterId?: string; guidedTargetCharacterId?: string
  autoOpen?: boolean; label?: string; status?: 'required' | 'completed' | string
  requiredTurnCount?: number; completedTurnCount?: number; reason?: string
}

type SuggestionKind = 'followup' | 'mainline' | 'deeper'
type ChatSuggestionInput = string | {
  text?: string; prompt?: string; value?: string; message?: string; content?: string
  type?: SuggestionKind | string; kind?: SuggestionKind | string; category?: SuggestionKind | string
  suggestionType?: SuggestionKind | string; intent?: SuggestionKind | string
  label?: string; displayLabel?: string
}
type SuggestedPrompt = { text: string; kind: SuggestionKind; label: string }

type ChatOpener = {
  stageDirection?: string; line?: string; dialogue?: string; suggestedPrompts?: ChatSuggestionInput[]
}

type ChatOpenerPayload = {
  opener?: ChatOpener | string; openingLine?: string; stageDirection?: string
  dialogue?: string; line?: string; suggestedPrompts?: ChatSuggestionInput[]; prompts?: ChatSuggestionInput[]; suggestions?: ChatSuggestionInput[]
}

type Snapshot = {
  runId: string; revision: number; nodeId: string
  player: { mbti: string; displayName: string; perspectiveCharacterId?: string }
  flags: { heat: number; clarity: number; publicImpression: number }
  affection: Record<string, number>; trust: Record<string, number>
  relationships: Record<string, RelationshipAxes>; attitudes: Record<string, string>
  eventLedger: StoryEvent[]; activeEventId: string | null
  storyArc: { phase: 'early' | 'middle' | 'late'; beatCount: number; activeMissionId: string | null; tension: number; reciprocity: number; uncertainty: number }
  storyEventLedger: unknown[]; storyMission: StoryMission | null
  focusCharacterId: string | null; letterRecipientId: string | null
  echoMemories: Memory[]; choiceHistory: unknown[]
  guidedTargetCharacterId?: string | null; pendingChat?: PendingChat | null
  pendingInteraction?: PendingChat | null
  chatOpeners?: Record<string, ChatOpenerPayload>
}

type Choice = { id: string; label: string; hint: string; characterId?: string; targetCharacterId?: string }
type StoryNode = {
  chapter: string; eyebrow: string; title: string; speaker: string; text: string
  textBeats?: string[]
  characterId?: string; speakerCharacterId?: string; cinematic?: string; choices: Choice[]
  sceneVideo?: string; backgroundVideo?: string; poster?: string
  media?: {
    assetId?: string; src?: string; poster?: string; available?: boolean
    status?: 'ready' | 'planned' | string
    fallback?: { kind?: string; src?: string; poster?: string }
  }
  mediaCue?: string; action?: string; eventId?: string
  gameBrief?: { name: string; format: string; winCondition: string }
  requiresMemory?: boolean; requiresEvent?: boolean; requiresGuidedInteraction?: boolean; characterChoice?: boolean; isEnding?: boolean
  allowDirector?: boolean
  guidedTargetCharacterId?: string | null; pendingChat?: PendingChat | null
  guidedInteraction?: PendingChat | null
}
type View = {
  snapshot: Snapshot; node: StoryNode; characters: Character[]
  guidedTargetCharacterId?: string | null; pendingChat?: PendingChat | null
  chatOpeners?: Record<string, ChatOpenerPayload>
}
type Receipt = { kind: string; intentId?: string; attitude?: string; publicReason?: string; patch?: Record<string, unknown>; eventActivation?: StoryEvent | null; mission?: StoryMission; title?: string; playerMissionPrompt?: string }

const PROGRESS: Record<string, number> = { 'arrival-context': 6, 'villa-arrival': 18, introductions: 32, 'cast-first-impressions': 41, 'icebreaker-choice': 49, 'guided-chat': 62, 'team-up': 76, 'anonymous-letter': 89, callback: 100, arrival: 8, 'first-look': 26, 'private-window': 48, 'event-reveal': 68 }
const ATTITUDE_LABELS: Record<string, string> = { warm: '温暖', curious: '好奇', guarded: '戒备', challenging: '试探', vulnerable: '袒露', softened: '松动', uncertain: '迟疑', honest: '坦诚', moved: '被触动', careful: '谨慎', steady: '稳定', boundary: '边界' }
const AXIS_LABELS: Record<string, string> = { trust: '信任', affection: '好感', respect: '尊重', fear: '压力', debt: '亏欠', attraction: '吸引', resentment: '芥蒂' }

type SceneMediaAsset = {
  assetId: string; src?: string; poster?: string; fallbackSrc: string; fallbackPoster?: string; cue?: string
}

const NODE_MEDIA: Record<string, SceneMediaAsset> = {
  'arrival-context': { assetId: 'D1-A1-island-hotel-establish', src: '/media/video/D1-A1-island-hotel-establish.mp4', poster: '/media/posters/D1-A1-island-hotel-establish.jpg', fallbackSrc: '/media/video/D1-A1-island-hotel-establish.mp4', fallbackPoster: '/media/posters/D1-A1-island-hotel-establish.jpg' },
  'villa-arrival': { assetId: 'D1-A2-villa-entry', src: '/media/video/D1-A2-villa-entry.mp4', poster: '/media/posters/D1-A2-villa-entry.jpg', fallbackSrc: '/media/video/D1-A2-villa-entry.mp4', fallbackPoster: '/media/posters/D1-A2-villa-entry.jpg' },
  introductions: { assetId: 'D1-A3-cast-introductions', src: '/media/video/D1-A3-cast-introductions.mp4', poster: '/media/posters/D1-A3-cast-introductions.jpg', fallbackSrc: '/media/video/D1-A3-cast-introductions.mp4', fallbackPoster: '/media/posters/D1-A3-cast-introductions.jpg' },
  'cast-first-impressions': { assetId: 'D1-A3B-cast-first-impressions', src: '/media/video/D1-A3B-cast-first-impressions.mp4', poster: '/media/posters/D1-A3B-cast-first-impressions.jpg', fallbackSrc: '/media/video/D1-A3B-cast-first-impressions.mp4', fallbackPoster: '/media/posters/D1-A3B-cast-first-impressions.jpg' },
  'icebreaker-choice': { assetId: 'D1-A4-icebreaker-selection', src: '/media/video/D1-A4-icebreaker-selection.mp4', poster: '/media/posters/D1-A4-icebreaker-selection.jpg', fallbackSrc: '/media/video/D1-A4-icebreaker-selection.mp4', fallbackPoster: '/media/posters/D1-A4-icebreaker-selection.jpg' },
  'guided-chat': { assetId: 'D1-A5-guided-smalltalk', src: '/media/video/D1-A5-guided-smalltalk.mp4', poster: '/media/posters/D1-A5-guided-smalltalk.jpg', fallbackSrc: '/media/video/D1-A5-guided-smalltalk.mp4', fallbackPoster: '/media/posters/D1-A5-guided-smalltalk.jpg' },
  'team-up': { assetId: 'D1-A6-first-dinner-team', src: '/media/video/D1-A6-first-dinner-team.mp4', poster: '/media/posters/D1-A6-first-dinner-team.jpg', fallbackSrc: '/media/video/D1-A6-first-dinner-team.mp4', fallbackPoster: '/media/posters/D1-A6-first-dinner-team.jpg' },
  'anonymous-letter': { assetId: 'D1-A7-heart-message', src: '/media/video/D1-A7-heart-message.mp4', poster: '/media/posters/D1-A7-heart-message.jpg', fallbackSrc: '/media/video/D1-A7-heart-message.mp4', fallbackPoster: '/media/posters/D1-A7-heart-message.jpg' },
  callback: { assetId: 'D2-A1-memory-callback', src: '/media/video/D2-A1-memory-callback.mp4', poster: '/media/posters/D2-A1-memory-callback.jpg', fallbackSrc: '/media/video/D2-A1-memory-callback.mp4', fallbackPoster: '/media/posters/D2-A1-memory-callback.jpg' },
}

// Every authored Story Director event has a deterministic stage projection. Its
// fallback remains bound to the same event asset, so a failed load can never
// substitute unrelated story footage.
const EVENT_MEDIA: Record<string, SceneMediaAsset> = {
  'story.kitchen.two-person-shift': { assetId: 'EV-KITCHEN-two-person-shift', src: '/media/video/EV-KITCHEN-two-person-shift.mp4', poster: '/media/posters/EV-KITCHEN-two-person-shift.jpg', fallbackSrc: '/media/video/EV-KITCHEN-two-person-shift.mp4', fallbackPoster: '/media/posters/EV-KITCHEN-two-person-shift.jpg' },
  'story.house.rules-friction': { assetId: 'EV-RULES-house-friction', src: '/media/video/EV-RULES-house-friction.mp4', poster: '/media/posters/EV-RULES-house-friction.jpg', fallbackSrc: '/media/video/EV-RULES-house-friction.mp4', fallbackPoster: '/media/posters/EV-RULES-house-friction.jpg' },
  'story.signal.first-anonymous-message': { assetId: 'EV-SIGNAL-first-anonymous-message', src: '/media/video/EV-SIGNAL-first-anonymous-message.mp4', poster: '/media/posters/EV-SIGNAL-first-anonymous-message.jpg', fallbackSrc: '/media/video/EV-SIGNAL-first-anonymous-message.mp4', fallbackPoster: '/media/posters/EV-SIGNAL-first-anonymous-message.jpg' },
  'story.identity.profession-reveal': { assetId: 'EV-IDENTITY-profession-reveal', src: '/media/video/EV-IDENTITY-profession-reveal.mp4', poster: '/media/posters/EV-IDENTITY-profession-reveal.jpg', fallbackSrc: '/media/video/EV-IDENTITY-profession-reveal.mp4', fallbackPoster: '/media/posters/EV-IDENTITY-profession-reveal.jpg' },
  'story.date.blind-box': { assetId: 'EV-DATE-blind-box', src: '/media/video/EV-DATE-blind-box.mp4', poster: '/media/posters/EV-DATE-blind-box.jpg', fallbackSrc: '/media/video/EV-DATE-blind-box.mp4', fallbackPoster: '/media/posters/EV-DATE-blind-box.jpg' },
  'story.date.mutual-signal': { assetId: 'EV-DATE-mutual-signal', src: '/media/video/EV-DATE-mutual-signal.mp4', poster: '/media/posters/EV-DATE-mutual-signal.jpg', fallbackSrc: '/media/video/EV-DATE-mutual-signal.mp4', fallbackPoster: '/media/posters/EV-DATE-mutual-signal.jpg' },
  'story.missed-timing.empty-seat': { assetId: 'EV-MISSED-empty-seat', src: '/media/video/EV-MISSED-empty-seat.mp4', poster: '/media/posters/EV-MISSED-empty-seat.jpg', fallbackSrc: '/media/video/EV-MISSED-empty-seat.mp4', fallbackPoster: '/media/posters/EV-MISSED-empty-seat.jpg' },
  'story.care.breakfast-callback': { assetId: 'EV-CARE-breakfast-callback', src: '/media/video/EV-CARE-breakfast-callback.mp4', poster: '/media/posters/EV-CARE-breakfast-callback.jpg', fallbackSrc: '/media/video/EV-CARE-breakfast-callback.mp4', fallbackPoster: '/media/posters/EV-CARE-breakfast-callback.jpg' },
  'story.triangle.reverse-invite': { assetId: 'EV-TRIANGLE-reverse-invite', src: '/media/video/EV-TRIANGLE-reverse-invite.mp4', poster: '/media/posters/EV-TRIANGLE-reverse-invite.jpg', fallbackSrc: '/media/video/EV-TRIANGLE-reverse-invite.mp4', fallbackPoster: '/media/posters/EV-TRIANGLE-reverse-invite.jpg' },
  'story.challenge.water-bridge': { assetId: 'EV-BRIDGE-hidden-courage', src: '/media/video/EV-BRIDGE-hidden-courage.mp4', poster: '/media/posters/EV-BRIDGE-hidden-courage.jpg', fallbackSrc: '/media/video/EV-BRIDGE-hidden-courage.mp4', fallbackPoster: '/media/posters/EV-BRIDGE-hidden-courage.jpg' },
  'story.group.truth-firepit': { assetId: 'EV-GROUP-truth-firepit', src: '/media/video/EV-GROUP-truth-firepit.mp4', poster: '/media/posters/EV-GROUP-truth-firepit.jpg', fallbackSrc: '/media/video/EV-GROUP-truth-firepit.mp4', fallbackPoster: '/media/posters/EV-GROUP-truth-firepit.jpg' },
  'story.bombshell.ninth-card': { assetId: 'EV-BOMBSHELL-ninth-card', src: '/media/video/EV-BOMBSHELL-ninth-card.mp4', poster: '/media/posters/EV-BOMBSHELL-ninth-card.jpg', fallbackSrc: '/media/video/EV-BOMBSHELL-ninth-card.mp4', fallbackPoster: '/media/posters/EV-BOMBSHELL-ninth-card.jpg' },
  'story.past.consent-reveal': { assetId: 'EV-PAST-consent-reveal', src: '/media/video/EV-PAST-consent-reveal.mp4', poster: '/media/posters/EV-PAST-consent-reveal.jpg', fallbackSrc: '/media/video/EV-PAST-consent-reveal.mp4', fallbackPoster: '/media/posters/EV-PAST-consent-reveal.jpg' },
  'story.trip.last-two-days': { assetId: 'EV-TRIP-last-two-days', src: '/media/video/EV-TRIP-last-two-days.mp4', poster: '/media/posters/EV-TRIP-last-two-days.jpg', fallbackSrc: '/media/video/EV-TRIP-last-two-days.mp4', fallbackPoster: '/media/posters/EV-TRIP-last-two-days.jpg' },
  'story.final.unsent-letter': { assetId: 'EV-FINAL-unsent-letter', src: '/media/video/EV-FINAL-unsent-letter.mp4', poster: '/media/posters/EV-FINAL-unsent-letter.jpg', fallbackSrc: '/media/video/EV-FINAL-unsent-letter.mp4', fallbackPoster: '/media/posters/EV-FINAL-unsent-letter.jpg' },
  'story.final.confession-day': { assetId: 'EV-FINAL-confession-day', src: '/media/video/EV-FINAL-confession-day.mp4', poster: '/media/posters/EV-FINAL-confession-day.jpg', fallbackSrc: '/media/video/EV-FINAL-confession-day.mp4', fallbackPoster: '/media/posters/EV-FINAL-confession-day.jpg' },
}

const FALLBACK_OPENERS: Record<string, { stageDirection: string; line: string }> = {
  shenmo: { stageDirection: '沈墨把座位卡向旁边挪了一点，给你留出空位。', line: '你好，我是沈墨。刚才大家介绍得都很快，我可能比较容易记住细节。你进门后最先注意到了什么？' },
  linyu: { stageDirection: '林屿给你倒了半杯温水，才在对面坐下。', line: '你好，我是林屿。先喝口水吧，一路过来应该挺累的。你现在还紧张吗？' },
  chengye: { stageDirection: '程野靠住椅背，笑着把镜头外的空位指给你。', line: '程野。刚才镜头太多，都没来得及好好打招呼。先不谈任务——这间小屋里，你最想去哪里看看？' },
  guyan: { stageDirection: '顾言放下手里的机械锁，像是在认真组织第一句话。', line: '你好，我是顾言。自我介绍这件事我不太擅长，不过我会认真听。你希望别人先认识你的哪一面？' },
  jiangwan: { stageDirection: '江晚合上写到一半的信纸，抬眼看向你。', line: '你好，我是江晚。刚才人多，很多话只来得及说一半。现在只有我们，你想从哪件小事开始聊？' },
  jiangmi: { stageDirection: '姜米把录音笔按下暂停，朝你晃了晃手。', line: '我是姜米。这里的海风比我想象中还大，但好像也比想象中更容易让人开口。你刚到小屋的第一感觉是什么？' },
  sunnian: { stageDirection: '苏念把果盘往你面前推了推，确认你坐得舒服才开口。', line: '你好，我是苏念。刚才一直在忙，都忘了问你有没有吃好。第一天还习惯吗？' },
  chensu: { stageDirection: '陈叙确认旧相机放稳了，拉开旁边的椅子。', line: '陈叙。刚把东西放好。你要是不介意，先坐会儿——刚来这里，还习惯吗？' },
}

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

function pendingCharacterId(pending?: PendingChat | null) {
  if (typeof pending === 'string') return pending
  if (!pending || typeof pending !== 'object') return null
  return pending.characterId || pending.targetCharacterId || pending.guidedTargetCharacterId || null
}

function resolveGuidedCharacterId(view: View) {
  return view.guidedTargetCharacterId
    || view.snapshot.guidedTargetCharacterId
    || view.node.guidedTargetCharacterId
    || pendingCharacterId(view.pendingChat)
    || pendingCharacterId(view.snapshot.pendingChat)
    || pendingCharacterId(view.node.pendingChat)
    || pendingCharacterId(view.snapshot.pendingInteraction)
    || pendingCharacterId(view.node.guidedInteraction)
    || null
}

function resolvePendingChat(view: View) {
  return view.pendingChat ?? view.snapshot.pendingChat ?? view.node.pendingChat ?? view.snapshot.pendingInteraction ?? view.node.guidedInteraction ?? null
}

function normalizeOpener(payload: ChatOpenerPayload | ChatOpener | string | undefined, fallback: { stageDirection: string; line: string }) {
  if (typeof payload === 'string') return { ...fallback, line: payload }
  if (!payload) return fallback
  const expanded = payload as ChatOpenerPayload & ChatOpener
  const nested = typeof expanded.opener === 'object' ? expanded.opener : undefined
  const nestedLine = typeof expanded.opener === 'string' ? expanded.opener : undefined
  return {
    stageDirection: nested?.stageDirection || expanded.stageDirection || fallback.stageDirection,
    line: nested?.line || nested?.dialogue || nestedLine || expanded.openingLine || expanded.line || expanded.dialogue || fallback.line,
  }
}

function promptsFromPayload(payload?: ChatOpenerPayload | ChatOpener | string) {
  if (!payload || typeof payload === 'string') return []
  const expanded = payload as ChatOpenerPayload & ChatOpener
  const nested = typeof expanded.opener === 'object' ? expanded.opener : undefined
  return nested?.suggestedPrompts || expanded.suggestedPrompts || expanded.prompts || expanded.suggestions || []
}

function suggestionKind(value?: string): SuggestionKind {
  const normalized = value?.toLowerCase().replace(/[_\s-]/g, '')
  if (normalized === 'mainline' || normalized === 'story' || normalized === 'advance' || normalized === '推进剧情') return 'mainline'
  if (normalized === 'deeper' || normalized === 'deep' || normalized === 'memory' || normalized === '深入了解') return 'deeper'
  return 'followup'
}

function normalizeSuggestion(input: ChatSuggestionInput, fallbackKind: SuggestionKind = 'followup'): SuggestedPrompt | null {
  if (typeof input === 'string') {
    const text = input.trim()
    return text ? { text, kind: fallbackKind, label: fallbackKind === 'mainline' ? '推进剧情' : fallbackKind === 'deeper' ? '深入了解' : '接着聊' } : null
  }
  const text = (input.text || input.prompt || input.value || input.message || input.content || input.label || '').trim()
  if (!text) return null
  const declaredKind = input.type || input.kind || input.category || input.suggestionType || input.intent
  const kind = declaredKind ? suggestionKind(declaredKind) : fallbackKind
  const standardLabel = kind === 'mainline' ? '推进剧情' : kind === 'deeper' ? '深入了解' : '接着聊'
  const label = input.displayLabel || (input.label && input.label !== text ? input.label : standardLabel)
  return { text, kind, label }
}

function fallbackPrompts(character: Character, perspective: Character | undefined, memories: Memory[], phase: Snapshot['storyArc']['phase'], nodeId: string): ChatSuggestionInput[] {
  const playerName = perspective?.name || '我'
  if (!memories.length) return [
    { text: `你好，我是${playerName}。刚才人多，没来得及好好认识你。`, type: 'followup', displayLabel: '先打招呼' },
    { text: '第一次来这种节目，你现在紧张吗？', type: 'deeper' },
    { text: nodeId === 'guided-chat' ? '节目组让我们记住对方一件真实的小事。你最希望我先记住什么？' : '你为什么会来《心动之旅》？', type: 'mainline' },
  ]
  const latest = memories[memories.length - 1]
  if (memories.length === 1 || phase === 'early') return [
    { text: `你还记得我刚才说的“${latest.playerText.slice(0, 24)}”吗？`, type: 'followup', displayLabel: '回忆回声' },
    { text: '和刚见面时比，你现在对我有什么新印象？', type: 'deeper' },
    { text: nodeId === 'guided-chat' ? '接下来的组队，你最想先从哪件事开始？' : (character.quickPrompts[0] || '你愿意和我一起试试下一个任务吗？'), type: 'mainline' },
  ]
  return [
    { text: `上次聊到“${(latest.summary || latest.playerText).slice(0, 22)}”，你后来还想过吗？`, type: 'followup', displayLabel: '回忆回声' },
    { text: character.quickPrompts[0] || '这次你想让我多了解你的哪一面？', type: 'deeper' },
    { text: '如果下一次任务要两个人一起做，你愿意和我试试吗？', type: 'mainline' },
  ]
}

function promptKeepsPlayerIdentity(prompt: string, perspective?: Character) {
  if (!perspective) return true
  const selfIntroduction = prompt.match(/(?:你好[，,。！!\s]*)?我(?:叫|是)\s*([\p{Script=Han}]{2,4})(?=[，,。！!\s]|$)/u)
  return !selfIntroduction || selfIntroduction[1] === perspective.name
}

function selectSuggestedPrompts(inputs: ChatSuggestionInput[], perspective: Character | undefined, firstGreeting?: SuggestedPrompt) {
  const legacyKinds: SuggestionKind[] = ['followup', 'mainline', 'deeper']
  const normalized = inputs
    .map((input, index) => normalizeSuggestion(input, legacyKinds[index % legacyKinds.length]))
    .filter((item): item is SuggestedPrompt => !!item && promptKeepsPlayerIdentity(item.text, perspective))
  const unique = normalized.filter((item, index, list) => list.findIndex(candidate => candidate.text === item.text) === index)
  const selected: SuggestedPrompt[] = []
  if (firstGreeting) selected.push(firstGreeting)
  const kinds: SuggestionKind[] = firstGreeting ? ['mainline', 'deeper', 'followup'] : ['followup', 'mainline', 'deeper']
  kinds.forEach(kind => {
    const candidate = unique.find(item => item.kind === kind && !selected.some(current => current.text === item.text))
    if (candidate && selected.length < 3) selected.push(candidate)
  })
  unique.forEach(item => {
    if (selected.length < 3 && !selected.some(current => current.text === item.text)) selected.push(item)
  })
  return selected.slice(0, 3)
}

function buildNarrationBeats(text: string, authoredBeats?: string[]) {
  const explicit = (authoredBeats || []).map(beat => beat.trim()).filter(Boolean)
  if (explicit.length) return explicit.slice(0, 4)
  const normalized = text.trim()
  if (!normalized || normalized.length <= 68) return [normalized]
  const clauses = normalized.match(/[^，。！？!?；;]+[，。！？!?；;]?/g)?.map(part => part.trim()).filter(Boolean) || [normalized]
  const desiredCount = Math.min(4, Math.max(2, Math.ceil(normalized.length / 66)))
  const targetLength = Math.ceil(normalized.length / desiredCount)
  const beats: string[] = []
  let current = ''
  clauses.forEach((clause, index) => {
    const remainingClauses = clauses.length - index
    const remainingSlots = desiredCount - beats.length
    if (current && current.length + clause.length > targetLength && remainingClauses >= remainingSlots) {
      beats.push(current)
      current = clause
    } else {
      current += clause
    }
  })
  if (current) beats.push(current)
  if (beats.length <= 4) return beats
  return [...beats.slice(0, 3), beats.slice(3).join('')]
}

function useTypewriter(beats: string[], presentationKey: string, paused = false) {
  const reducedMotion = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const signature = beats.join('\u241e')
  const firstBeat = beats[0] || ''
  const firstFrameLength = reducedMotion && firstBeat ? 1 : 0
  const [state, setState] = useState({ key: presentationKey, beatIndex: 0, visibleLength: firstFrameLength, readyForChoices: false })
  useEffect(() => {
    // Even with reduced motion, do not reveal a new scene in full on its first
    // paint. One deliberate tap reveals the whole passage; the following tap
    // alone unlocks choices. This keeps the authored reading beat deterministic.
    setState({ key: presentationKey, beatIndex: 0, visibleLength: reducedMotion && firstBeat ? 1 : 0, readyForChoices: false })
  }, [firstBeat, presentationKey, reducedMotion, signature])
  const isCurrent = state.key === presentationKey
  const beatIndex = isCurrent ? Math.min(state.beatIndex, Math.max(0, beats.length - 1)) : 0
  const currentBeat = beats[beatIndex] || ''
  useEffect(() => {
    if (paused || reducedMotion || !currentBeat || !isCurrent) return
    const timer = window.setInterval(() => {
      setState(current => {
        if (current.key !== presentationKey || current.beatIndex !== beatIndex || current.visibleLength >= currentBeat.length) {
          window.clearInterval(timer)
          return current
        }
        return { ...current, visibleLength: Math.min(currentBeat.length, current.visibleLength + 1) }
      })
    }, 52)
    return () => window.clearInterval(timer)
  }, [beatIndex, currentBeat, isCurrent, paused, presentationKey, reducedMotion])
  const visibleLength = isCurrent ? state.visibleLength : 0
  const readyForChoices = isCurrent && state.readyForChoices
  const complete = visibleLength >= currentBeat.length
  const isLastBeat = beatIndex >= beats.length - 1
  const reveal = () => {
    if (paused) return
    setState(current => {
      if (current.key !== presentationKey) return { key: presentationKey, beatIndex: 0, visibleLength: firstBeat.length, readyForChoices: false }
      const activeBeat = beats[current.beatIndex] || ''
      if (current.visibleLength < activeBeat.length) return { ...current, visibleLength: activeBeat.length, readyForChoices: false }
      if (current.beatIndex < beats.length - 1) {
        const nextBeatIndex = current.beatIndex + 1
        const nextBeat = beats[nextBeatIndex] || ''
        return { ...current, beatIndex: nextBeatIndex, visibleLength: reducedMotion && nextBeat ? 1 : 0, readyForChoices: false }
      }
      return { ...current, readyForChoices: true }
    })
  }
  return { text: currentBeat.slice(0, visibleLength), complete, readyForChoices, reveal, beatIndex, beatCount: beats.length, isLastBeat }
}

type StoryOverlayPhase = 'narration' | 'narration-exit' | 'interaction'

function useStoryOverlayPhase(readyForChoices: boolean, presentationKey: string): StoryOverlayPhase {
  const [state, setState] = useState<{ key: string; phase: StoryOverlayPhase }>({ key: presentationKey, phase: 'narration' })
  const phase = state.key === presentationKey ? state.phase : 'narration'
  useEffect(() => {
    setState({ key: presentationKey, phase: 'narration' })
  }, [presentationKey])
  useEffect(() => {
    if (!readyForChoices) return
    setState(current => current.key === presentationKey
      ? { ...current, phase: 'narration-exit' }
      : { key: presentationKey, phase: 'narration' })
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const timer = window.setTimeout(() => {
      setState(current => current.key === presentationKey
        ? { ...current, phase: 'interaction' }
        : current)
    }, reducedMotion ? 20 : 280)
    return () => window.clearTimeout(timer)
  }, [presentationKey, readyForChoices])
  return phase
}

type AudioOwner = { video: HTMLVideoElement; mute: () => void }
let activeAudioOwner: AudioOwner | null = null
let audioIntentUnlocked = false

function unlockAudioIntent() {
  audioIntentUnlocked = true
}

function claimAudioOwner(video: HTMLVideoElement, mute: () => void) {
  if (activeAudioOwner?.video !== video) activeAudioOwner?.mute()
  activeAudioOwner = { video, mute }
}

function releaseAudioOwner(video: HTMLVideoElement) {
  if (activeAudioOwner?.video === video) activeAudioOwner = null
}

function useEventPlayback(videoRef: React.RefObject<HTMLVideoElement>, src: string, active: boolean, firstPassConsumed = false) {
  const [phase, setPhase] = useState<'first' | 'loop'>(firstPassConsumed ? 'loop' : 'first')
  const [muted, setMuted] = useState(firstPassConsumed || !audioIntentUnlocked)
  const [needsGesture, setNeedsGesture] = useState(!firstPassConsumed && !audioIntentUnlocked)
  const mutedRef = useRef(muted)
  const phaseRef = useRef(phase)
  mutedRef.current = muted
  phaseRef.current = phase

  const muteFromCoordinator = () => {
    const video = videoRef.current
    if (video) video.muted = true
    mutedRef.current = true
    setMuted(true)
  }

  useEffect(() => {
    const nextPhase = firstPassConsumed ? 'loop' : 'first'
    const nextMuted = firstPassConsumed || !audioIntentUnlocked
    phaseRef.current = nextPhase
    mutedRef.current = nextMuted
    setPhase(nextPhase)
    setMuted(nextMuted)
    setNeedsGesture(!firstPassConsumed && !audioIntentUnlocked)
    const video = videoRef.current
    if (video) {
      video.pause()
      video.currentTime = 0
      video.muted = nextMuted
    }
  }, [firstPassConsumed, src, videoRef])

  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    let cancelled = false
    const play = () => {
      if (!active || document.hidden) {
        video.pause()
        releaseAudioOwner(video)
        return
      }
      video.muted = mutedRef.current
      if (!video.muted) claimAudioOwner(video, muteFromCoordinator)
      void video.play().catch(() => {
        if (cancelled || video.muted) return
        // Browsers may reject unmuted autoplay even after an earlier entry
        // gesture. Fall back to motion immediately and surface an explicit,
        // one-tap sound affordance instead of failing playback altogether.
        video.muted = true
        mutedRef.current = true
        setMuted(true)
        setNeedsGesture(true)
        releaseAudioOwner(video)
        void video.play().catch(() => undefined)
      })
    }
    play()
    document.addEventListener('visibilitychange', play)
    return () => {
      cancelled = true
      document.removeEventListener('visibilitychange', play)
      video.pause()
      releaseAudioOwner(video)
    }
  }, [active, muted, src, videoRef])

  const toggleSound = () => {
    unlockAudioIntent()
    const video = videoRef.current
    const nextMuted = !mutedRef.current
    mutedRef.current = nextMuted
    setMuted(nextMuted)
    setNeedsGesture(false)
    if (!video) return
    video.muted = nextMuted
    if (nextMuted) {
      releaseAudioOwner(video)
      return
    }
    claimAudioOwner(video, muteFromCoordinator)
    void video.play().catch(() => {
      video.muted = true
      mutedRef.current = true
      setMuted(true)
      setNeedsGesture(true)
      releaseAudioOwner(video)
    })
  }

  const handleEnded = () => {
    const video = videoRef.current
    if (!video) return
    const isFirstPass = phaseRef.current === 'first'
    const nextMuted = isFirstPass ? true : mutedRef.current
    if (isFirstPass) {
      phaseRef.current = 'loop'
      setPhase('loop')
      mutedRef.current = true
      setMuted(true)
      setNeedsGesture(false)
    }
    video.currentTime = 0
    video.muted = nextMuted
    if (nextMuted) releaseAudioOwner(video)
    else claimAudioOwner(video, muteFromCoordinator)
    if (active && !document.hidden) void video.play().catch(() => undefined)
  }

  return {
    muted,
    phase,
    needsGesture,
    toggleSound,
    handleEnded,
    soundLabel: needsGesture ? '点此开启声音' : muted ? (phase === 'loop' ? '循环已静音' : '声音已关闭') : '声音已开启',
  }
}

function MediaVideo({ src, className = '', poster, onError, onCanPlay, active = true, preload }: {
  src: string; className?: string; poster?: string; onError?: () => void; onCanPlay?: () => void; active?: boolean; preload?: 'none' | 'metadata' | 'auto'
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  useEffect(() => {
    const video = videoRef.current
    if (!video) return
    const syncPlayback = () => {
      if (!active || document.hidden) video.pause()
      else void video.play().catch(() => undefined)
    }
    syncPlayback()
    document.addEventListener('visibilitychange', syncPlayback)
    return () => document.removeEventListener('visibilitychange', syncPlayback)
  }, [active, src])
  return <video ref={videoRef} className={className} src={src} poster={poster} autoPlay={active} muted loop playsInline preload={preload || (active ? 'metadata' : 'none')} onCanPlay={onCanPlay} onError={onError} />
}

function EventMediaVideo({ src, className = '', poster, onError, onCanPlay, active, preload, firstPassConsumed = false }: {
  src: string; className?: string; poster?: string; onError?: () => void; onCanPlay?: () => void
  active: boolean; preload?: 'none' | 'metadata' | 'auto'; firstPassConsumed?: boolean
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const playback = useEventPlayback(videoRef, src, active, firstPassConsumed)
  return <>
    <video ref={videoRef} className={className} src={src} poster={poster} autoPlay={active} muted={playback.muted} playsInline preload={preload || (active ? 'auto' : 'metadata')} onCanPlay={onCanPlay} onError={onError} onEnded={playback.handleEnded} />
    {active && <button type="button" className={`scene-audio-toggle ${playback.needsGesture ? 'scene-audio-toggle--attention' : ''}`} onClick={playback.toggleSound} aria-label={playback.muted ? '开启视频声音' : '关闭视频声音'} aria-pressed={!playback.muted}>
      <span aria-hidden="true">{playback.muted ? '🔇' : '🔊'}</span><b>{playback.soundLabel}</b>
    </button>}
  </>
}

function SceneMedia({ src, poster, fallbackSrc, fallbackPoster, active, cue, assetId, firstPassConsumed = false, soundEnabled = true }: {
  src: string; poster?: string; fallbackSrc?: string; fallbackPoster?: string
  active: boolean; cue?: string; assetId?: string; firstPassConsumed?: boolean; soundEnabled?: boolean
}) {
  const [layers, setLayers] = useState(() => [{ src, poster }])
  const [visibleSrc, setVisibleSrc] = useState(src)
  const desiredSrcRef = useRef(src)
  const fallbackRef = useRef({ src: fallbackSrc, poster: fallbackPoster })
  const promotionRef = useRef('')
  const promotionTimerRef = useRef<number | null>(null)
  useEffect(() => {
    desiredSrcRef.current = src
    fallbackRef.current = { src: fallbackSrc, poster: fallbackPoster }
    promotionRef.current = ''
    if (promotionTimerRef.current) window.clearTimeout(promotionTimerRef.current)
    setLayers(current => {
      const desired = { src, poster }
      const existing = current.find(layer => layer.src === src)
      if (existing) return current.map(layer => layer.src === src ? desired : layer).slice(-2)
      return [...current.slice(-1), desired]
    })
    return () => {
      if (promotionTimerRef.current) window.clearTimeout(promotionTimerRef.current)
    }
  }, [fallbackPoster, fallbackSrc, poster, src])
  const promote = (readySrc: string) => {
    if (readySrc !== desiredSrcRef.current || promotionRef.current === readySrc) return
    promotionRef.current = readySrc
    setVisibleSrc(readySrc)
    promotionTimerRef.current = window.setTimeout(() => {
      setLayers(current => current.filter(layer => layer.src === readySrc))
      promotionTimerRef.current = null
    }, 420)
  }
  const reject = (failedSrc: string) => {
    if (failedSrc !== desiredSrcRef.current) return
    const fallback = fallbackRef.current
    if (fallback.src && fallback.src !== failedSrc) {
      desiredSrcRef.current = fallback.src
      promotionRef.current = ''
      setLayers(current => {
        const retained = current.filter(layer => layer.src !== failedSrc && layer.src !== fallback.src)
        return [...retained.slice(-1), { src: fallback.src as string, poster: fallback.poster }]
      })
      return
    }
    setLayers(current => current.length > 1 ? current.filter(layer => layer.src !== failedSrc) : current)
  }
  return <div className="scene-media" data-media-cue={cue || undefined} data-media-asset-id={assetId || undefined} role={cue ? 'img' : undefined} aria-label={cue ? `剧情动态画面：${cue}` : undefined}>
    {poster && <img className="scene-media__poster" src={poster} alt="" aria-hidden="true" />}
    {layers.map(layer => soundEnabled ? <EventMediaVideo
        key={layer.src}
        className={`scene-media__layer ${visibleSrc === layer.src ? 'scene-media__layer--visible' : ''}`}
        src={layer.src}
        poster={layer.poster}
        active={active && visibleSrc === layer.src}
        firstPassConsumed={firstPassConsumed && visibleSrc === layer.src}
        preload={desiredSrcRef.current === layer.src ? 'auto' : 'metadata'}
        onCanPlay={() => promote(layer.src)}
        onError={() => reject(layer.src)}
      /> : <MediaVideo
        key={layer.src}
        className={`scene-media__layer ${visibleSrc === layer.src ? 'scene-media__layer--visible' : ''}`}
        src={layer.src}
        poster={layer.poster}
        active={active && visibleSrc === layer.src}
        preload={desiredSrcRef.current === layer.src ? 'auto' : 'metadata'}
        onCanPlay={() => promote(layer.src)}
        onError={() => reject(layer.src)}
      />)}
  </div>
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

function Landing({ characters, onStart, busy }: { characters: Character[]; onStart: (mbti: string, perspectiveCharacterId: string) => void; busy: boolean }) {
  const [phase, setPhase] = useState<'intro' | 'cast'>('intro')
  const [selectedId, setSelectedId] = useState(characters[0]?.id || '')
  const selected = characters.find(character => character.id === selectedId) || characters[0]
  const backgroundVideo = phase === 'cast' && selected ? selected.video : '/media/video/E01-arrival-reveal.mp4'
  return (
    <main className={`landing landing--${phase}`}>
      <div className="landing-media" aria-hidden="true">
        <SceneMedia src={backgroundVideo} poster={selected?.portrait} active soundEnabled={false} />
        <div className="landing-scrim" />
        <div className="sun-glow" />
      </div>
      <header className="landing-topbar">
        <span>全球首档 MBTI 沉浸式恋爱实验</span>
        <span className="live-pill"><i /> DAY 1</span>
      </header>
      {phase === 'intro' ? <>
        <section className="landing-copy landing-copy--intro">
          <p className="landing-overline">7 天 6 夜 · 海岛心动酒店</p>
          <div className="title-lockup"><h1>心动之旅</h1><HeartMark /><p>MBTI 恋爱观察实验</p></div>
        </section>
        <section className="show-premise glass-card">
          <span>欢迎入住</span>
          <h2>七天六夜，故事从第一声“你好”开始。</h2>
          <p>欢迎来到《心动之旅》。八位来自不同生活轨迹的嘉宾，将在海岛酒店一起生活七天六夜。从初次见面、一起做饭，到组队约会和每晚的心动短信，共同生活的衣食住行会碰撞出怎样的火花？让我们一起期待。</p>
          <blockquote>帮助别人，也照见自己。找到一位愿意同行的人，更好地发现自己、爱自己。</blockquote>
          <button className="primary-button start-button" onClick={() => { unlockAudioIntent(); setPhase('cast') }}><span>认识本季八位嘉宾</span><i>→</i></button>
        </section>
      </> : selected && <>
        <section className="landing-copy landing-copy--cast">
          <p className="landing-overline">选择你的观察视角</p>
          <h1 className="selected-name">{selected.name}</h1>
          <p className="selected-tagline">{selected.mbti} · {selected.tagline}</p>
        </section>
        <section className="cast-picker" aria-label="选择观察人物">
          {characters.map(character => <button key={character.id} className={character.id === selected.id ? 'active' : ''} onClick={() => setSelectedId(character.id)} style={{ '--accent': character.accent } as React.CSSProperties} aria-pressed={character.id === selected.id} aria-label={`从${character.name}，${character.mbti}，${character.tagline}的视角进入`}>
            <img src={character.portrait} alt="" />
            <span className="cast-picker__copy"><b>{character.name}</b><em>{character.mbti}</em><small>{character.tagline}</small></span>
          </button>)}
        </section>
        <section className="character-preview glass-card" style={{ '--accent': selected.accent } as React.CSSProperties}>
          <div className="character-preview__heading"><span>{selected.mbti}</span><small>观察视角只决定开场线索，不替 TA 做选择</small></div>
          <h2>{selected.publicMask}</h2>
          <p>{selected.independentInterest}</p>
          <dl><div><dt>表达方式</dt><dd>{selected.voice}</dd></div><div><dt>关系边界</dt><dd>{selected.boundary}</dd></div></dl>
          <button className="primary-button start-button" disabled={busy} onClick={() => { unlockAudioIntent(); onStart(selected.mbti, selected.id) }}><span>{busy ? '正在开启…' : `跟随${selected.name}进入小屋`}</span><i>→</i></button>
          <button className="back-to-intro" onClick={() => setPhase('intro')}>← 返回节目介绍</button>
        </section>
      </>}
    </main>
  )
}

function CharacterDock({ characters, snapshot, guidedCharacterId, guidedComplete = false, onOpen }: {
  characters: Character[]; snapshot: Snapshot; guidedCharacterId?: string | null; guidedComplete?: boolean; onOpen: (character: Character) => void
}) {
  const guidedRef = useRef<HTMLButtonElement>(null)
  const perspectiveCharacter = characters.find(character => character.id === snapshot.player.perspectiveCharacterId) || characters.find(character => character.isPlayerPerspective)
  const availableCharacters = characters.filter(character => character.id !== perspectiveCharacter?.id && !character.isPlayerPerspective)
  const guidedCharacter = availableCharacters.find(character => character.id === guidedCharacterId)
  const dockCharacters = guidedCharacter
    ? [perspectiveCharacter, guidedCharacter].filter((character): character is Character => !!character)
    : [perspectiveCharacter, ...availableCharacters].filter((character): character is Character => !!character)
  useEffect(() => {
    if (guidedCharacter) guidedRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
  }, [guidedCharacter?.id, snapshot.nodeId])
  return (
    <nav className={`character-dock ${guidedCharacter ? 'character-dock--guided' : ''}`} aria-label="1 对 1 心动私聊">
      <div className="dock-label">
        <span>{guidedCharacter ? (guidedComplete ? '这次交流已完成' : '该你开口了') : '心动小屋'}</span>
        <small>{guidedCharacter ? (guidedComplete ? `${guidedCharacter.name}已记住这次对话` : `去和${guidedCharacter.name}打个招呼`) : '选一位嘉宾 1 对 1 交流'}</small>
      </div>
      <div className="dock-scroll">
        {dockCharacters.map((character) => {
          const memoryCount = snapshot.echoMemories.filter(m => m.characterId === character.id).length
          const guided = character.id === guidedCharacter?.id
          const isSelf = character.id === snapshot.player.perspectiveCharacterId || character.isPlayerPerspective === true
          const chatUnavailable = isSelf || character.chatEnabled === false
          return (
            <button ref={guided ? guidedRef : undefined} className={`dock-avatar ${guided ? 'dock-avatar--guided' : ''} ${chatUnavailable ? 'dock-avatar--unavailable' : ''} ${isSelf ? 'dock-avatar--self' : ''}`} key={character.id} onClick={() => !chatUnavailable && onOpen(character)} disabled={chatUnavailable} style={{ '--accent': character.accent } as React.CSSProperties} aria-label={isSelf ? `${character.name}，你的当前视角，不可与自己私聊` : chatUnavailable ? `${character.name}，当前暂不可私聊` : guided ? `剧情正在等你，与${character.name}交流` : `与${character.name}交流，${character.mbti}，${character.tagline}`}>
              <span className="dock-avatar__photo"><img src={character.portrait} alt="" />{(guided || memoryCount > 0) && <i className={guided ? `guided-badge ${guidedComplete ? 'guided-badge--done' : ''}` : ''}>{guided ? (guidedComplete ? '✓' : 1) : memoryCount}</i>}</span>
              <span className="dock-avatar__copy"><span><b>{character.name}</b><em>{character.mbti}</em></span><small>{isSelf ? '你的视角 · 不可私聊' : chatUnavailable ? '当前剧情中暂不可私聊' : character.tagline}</small></span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}

function ChatSheet({ character, characters, snapshot, embeddedOpener, onClose, onSend, busy }: {
  character: Character; characters: Character[]; snapshot: Snapshot; embeddedOpener?: ChatOpenerPayload
  onClose: () => void
  onSend: (message: string) => Promise<void>; busy: boolean
}) {
  const [draft, setDraft] = useState('')
  const firstLoadRef = useRef(true)
  const endpointSupportedRef = useRef(true)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const streamRef = useRef<HTMLDivElement>(null)
  const memories = snapshot.echoMemories.filter(memory => memory.characterId === character.id)
  const latest = memories[memories.length - 1]
  const perspective = characters.find(item => item.id === snapshot.player.perspectiveCharacterId) || characters.find(item => item.isPlayerPerspective)
  const baseFallback = FALLBACK_OPENERS[character.id] || {
    stageDirection: `${character.name}给你留出了一个可以慢慢说话的位置。`,
    line: `你好，我是${character.name}。刚才大家都在，还没来得及好好认识你。现在感觉怎么样？`,
  }
  const fallback = latest ? {
    stageDirection: `${character.name}看到你回来，把话题留在了上次停下的地方。`,
    line: `你回来了。上次你说到“${(latest.summary || latest.playerText).slice(0, 32)}”，我还记得。今天想先从哪里聊起？`,
  } : baseFallback
  const initialCardOpener = character.opener || character.openingLine
  const initialPayload = embeddedOpener || snapshot.chatOpeners?.[character.id] || (initialCardOpener ? { opener: initialCardOpener, suggestedPrompts: character.suggestedPrompts } : undefined)
  const [opener, setOpener] = useState(() => normalizeOpener(initialPayload, fallback))
  const [openerVisible, setOpenerVisible] = useState(!!initialPayload)
  const [openerLoading, setOpenerLoading] = useState(!initialPayload)
  const [remotePrompts, setRemotePrompts] = useState<ChatSuggestionInput[]>(() => promptsFromPayload(initialPayload))
  const axes = snapshot.relationships?.[character.id]
  const attitude = snapshot.attitudes?.[character.id] || 'curious'
  useEffect(() => {
    const currentEmbedded = embeddedOpener || snapshot.chatOpeners?.[character.id]
    if (currentEmbedded) {
      if (firstLoadRef.current) {
        setOpener(normalizeOpener(currentEmbedded, fallback))
        setOpenerVisible(true)
      }
      setRemotePrompts(promptsFromPayload(currentEmbedded))
      setOpenerLoading(false)
      firstLoadRef.current = false
      return
    }
    if (!endpointSupportedRef.current) {
      setOpener(fallback); setOpenerVisible(true); setOpenerLoading(false); firstLoadRef.current = false
      return
    }
    let cancelled = false
    const initialLoad = firstLoadRef.current
    const grace = initialLoad ? window.setTimeout(() => {
      if (!cancelled) { setOpener(fallback); setOpenerVisible(true) }
    }, 650) : undefined
    if (initialLoad) setOpenerLoading(true)
    api<ChatOpenerPayload>(`/api/runs/${snapshot.runId}/agents/${character.id}/opener?revision=${snapshot.revision}`)
      .then(payload => {
        if (cancelled) return
        if (initialLoad) { setOpener(normalizeOpener(payload, fallback)); setOpenerVisible(true) }
        const generatedPrompts = promptsFromPayload(payload)
        if (generatedPrompts.length) setRemotePrompts(generatedPrompts)
      })
      .catch(() => {
        if (cancelled) return
        endpointSupportedRef.current = false
        if (initialLoad) { setOpener(fallback); setOpenerVisible(true) }
      })
      .finally(() => {
        if (cancelled) return
        if (grace) window.clearTimeout(grace)
        setOpenerLoading(false); firstLoadRef.current = false
      })
    return () => { cancelled = true; if (grace) window.clearTimeout(grace) }
  }, [character.id, embeddedOpener, snapshot.chatOpeners, snapshot.revision, snapshot.runId])
  const firstGreeting: SuggestedPrompt = { text: `你好，我是${perspective?.name || '新来的嘉宾'}。刚才人多，没来得及好好认识你。`, kind: 'followup', label: '先打招呼' }
  const fallbackSuggestions = fallbackPrompts(character, perspective, memories, snapshot.storyArc.phase, snapshot.nodeId)
  const latestSuggestions = latest?.suggestions || latest?.suggestedPrompts || []
  const suggestedPrompts = selectSuggestedPrompts(
    [...latestSuggestions, ...remotePrompts, ...fallbackSuggestions],
    perspective,
    memories.length ? undefined : firstGreeting,
  )
  useEffect(() => {
    // Keep the independent history viewport pinned to the newest turn after
    // the opener resolves, the player sends, or the Agent reply arrives.
    const scrollToEnd = () => {
      const stream = streamRef.current
      if (!stream) return
      stream.scrollTo({ top: stream.scrollHeight, behavior: 'smooth' })
    }
    const frame = window.requestAnimationFrame(scrollToEnd)
    const settle = window.setTimeout(scrollToEnd, 160)
    return () => { window.cancelAnimationFrame(frame); window.clearTimeout(settle) }
  }, [busy, character.id, latest?.id, memories.length, openerLoading, openerVisible])
  const submit = async (event?: FormEvent) => {
    event?.preventDefault()
    const message = draft.trim()
    if (!message || busy) return
    setDraft('')
    await onSend(message)
  }
  return (
    <div className="sheet-backdrop" role="dialog" aria-modal="true" aria-label={`与${character.name}私聊`}>
      <section className={`chat-sheet ${memories.length || busy ? 'chat-sheet--has-history' : ''}`} style={{ '--accent': character.accent } as React.CSSProperties}>
        <div className="chat-portrait">
          <div className="chat-portrait__media">
            <img className="chat-portrait__blur" src={character.portrait} alt="" />
            <EventMediaVideo className="chat-portrait__subject" src={character.video} poster={character.portrait} active firstPassConsumed />
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
          <div className="message-stream" ref={streamRef} role="log" aria-live="polite" aria-label={`与${character.name}的对话记录`} tabIndex={0}>
            {!openerVisible && <div className="message agent opener-loading" aria-live="polite"><b>{character.name}正在朝你走来</b><span><i /><i /><i /></span><small>正在结合此刻的剧情和你们的记忆…</small></div>}
            {openerVisible && <div className="message agent conversation-opener"><b>{character.name} · {latest ? '又见面了' : '初次寒暄'}</b><em>{opener.stageDirection}</em><p>{opener.line}</p>{openerLoading && <small>正在读取此刻更贴近人物卡的表达…</small>}</div>}
            {memories.slice(-10).map(memory => (
              <div className="message-pair" key={memory.id}>
                <div className="message player"><p>{memory.playerText}</p></div>
                <div className="message agent"><b>{character.name} · {ATTITUDE_LABELS[memory.attitude] || memory.attitude}</b>{memory.stageDirection && <em>{memory.stageDirection}</em>}<p>{memory.agentReply}</p><small>{memory.summary || '已写入你们的共同记忆'}</small></div>
              </div>
            ))}
            {busy && <div className="message agent typing"><i /><i /><i /></div>}
            <div className="message-stream__end" aria-hidden="true" />
          </div>
          <div className="quick-prompts" aria-label="对话建议">
            {suggestedPrompts.map((prompt, index) => <button className={`quick-prompt quick-prompt--${prompt.kind}`} key={`${index}-${prompt.kind}-${prompt.text}`} onClick={() => { setDraft(prompt.text); inputRef.current?.focus() }} aria-label={`${prompt.label}：${prompt.text}`}><i>{prompt.label}</i>{prompt.text}</button>)}
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

function Cinematic({ src, title, onDone }: { src: string; title: string; onDone: () => void }) {
  const [ready, setReady] = useState(false)
  const [showTitle, setShowTitle] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const playback = useEventPlayback(videoRef, src, true)
  useEffect(() => {
    if (!ready) return
    setShowTitle(true)
    const timer = window.setTimeout(() => setShowTitle(false), 2600)
    return () => window.clearTimeout(timer)
  }, [ready, src])
  return (
    <div className="cinematic-overlay" role="dialog" aria-modal="true" aria-label={title} data-playback-mode="first-pass-autoclose">
      <video ref={videoRef} src={src} autoPlay muted={playback.muted} playsInline onCanPlay={() => setReady(true)} onEnded={onDone} onError={onDone} />
      <div className="cinematic-grade" />
      <div className={`cinematic-title ${showTitle ? 'show' : ''}`}><span>HEART JOURNEY · STORY EVENT</span><b>{title}</b></div>
      <div className="cinematic-controls">
        <button type="button" className={playback.needsGesture ? 'audio-attention' : ''} onClick={playback.toggleSound} aria-label={playback.muted ? '开启视频声音' : '关闭视频声音'} aria-pressed={!playback.muted}><span aria-hidden="true">{playback.muted ? '🔇' : '🔊'}</span>{playback.soundLabel}</button>
        <button type="button" onClick={onDone}>跳过 →</button>
      </div>
    </div>
  )
}

function ReceiptToast({ receipt }: { receipt: Receipt }) {
  const patchCount = Object.keys(receipt.patch || {}).length
  const title = receipt.eventActivation ? `事件激活 · ${receipt.eventActivation.label}` : receipt.kind === 'agent-turn' ? `态度更新 · ${ATTITUDE_LABELS[receipt.attitude || ''] || receipt.attitude}` : receipt.kind === 'story-event' ? `新主任务 · ${receipt.mission?.title || receipt.title}` : receipt.kind === 'story-director-wait' ? '导演判断 · 继续积累证据' : receipt.kind === 'story-mission-resolution' ? '主任务结果已写入' : '选择已写入故事'
  const detail = receipt.eventActivation?.text || receipt.mission?.prompt || receipt.playerMissionPrompt || receipt.publicReason || (patchCount ? `${patchCount} 项关系参数已提交` : '剧情状态已提交')
  return <div className="receipt-toast"><HeartMark small /><div><b>{title}</b><span>{detail}</span></div></div>
}

function DirectorMission({ mission, characters, busy, onResolve }: { mission: StoryMission; characters: Character[]; busy: boolean; onResolve: (outcome: 'completed' | 'declined') => void }) {
  const names = mission.participantIds.map(id => characters.find(character => character.id === id)?.name).filter(Boolean).join('、')
  return (
    <section className={`director-mission director-mission--${mission.urgency}`}>
      <div className="director-mission__label"><span>MAIN QUEST</span><i>{mission.deadline}</i></div>
      <h2>{mission.title}</h2>
      <p>{mission.bridgeText}</p>
      {mission.sceneSetup && <div className="director-mission__setup"><b>现场发生了什么</b><span>{mission.sceneSetup}</span></div>}
      {mission.reversalBeat && <div className="director-mission__reversal"><b>意外变化</b><span>{mission.reversalBeat}</span>{mission.characterInsight && <small>{mission.characterInsight}</small>}</div>}
      <div className="director-mission__objective"><b>现在去做</b><span>{mission.prompt}</span></div>
      {!!mission.availableStrategies?.length && <div className="director-mission__strategies"><b>你可采用的策略</b>{mission.availableStrategies.map(item => <span key={item}>· {item}</span>)}</div>}
      <div className="director-mission__meta"><span>{names || '心动小屋'}</span><small>完成证据：{mission.successEvidence}</small></div>
      <div className="director-mission__actions">
        <button disabled={busy} onClick={() => onResolve('completed')}>我已完成</button>
        <button disabled={busy} onClick={() => onResolve('declined')}>这次不参加</button>
      </div>
      <small className="director-mission__exit">退出路径：{mission.exit}</small>
    </section>
  )
}

function GameBrief({ brief }: { brief: NonNullable<StoryNode['gameBrief']> }) {
  return <section className="game-brief">
    <div className="game-brief__title"><span>本轮游戏</span><h2>{brief.name}</h2></div>
    <dl><div><dt>怎么玩</dt><dd>{brief.format}</dd></div><div><dt>怎样算赢</dt><dd>{brief.winCondition}</dd></div></dl>
  </section>
}

function resolveSceneMedia(view: View, guidedCharacterId?: string | null) {
  const { snapshot, node, characters } = view
  const legacyNodeId: Record<string, string> = { arrival: 'arrival-context', 'first-look': 'introductions', 'private-window': 'guided-chat', 'event-reveal': 'team-up', 'heart-message': 'anonymous-letter' }
  const projectedNodeId = legacyNodeId[snapshot.nodeId] || snapshot.nodeId
  const nodeAsset = NODE_MEDIA[projectedNodeId] || NODE_MEDIA['arrival-context']
  const eventId = snapshot.storyMission?.eventId || node.eventId || (snapshot.activeEventId && EVENT_MEDIA[snapshot.activeEventId] ? snapshot.activeEventId : undefined)
  const eventAsset = eventId ? EVENT_MEDIA[eventId] : undefined
  const missionMedia = snapshot.storyMission?.media
  const missionMediaReady = !!missionMedia?.src && missionMedia.available !== false && missionMedia.status !== 'planned'
  const nodeMediaReady = !!node.media?.src && node.media.available !== false && node.media.status !== 'planned'
  const explicitNodeSrc = node.sceneVideo || node.backgroundVideo || (nodeMediaReady ? node.media?.src : undefined)
  const guidedCharacter = projectedNodeId === 'guided-chat' && guidedCharacterId
    ? characters.find(character => character.id === guidedCharacterId)
    : undefined
  if (snapshot.storyMission && eventAsset) return {
    src: (missionMediaReady ? missionMedia?.src : undefined) || eventAsset.src || eventAsset.fallbackSrc,
    poster: (missionMediaReady ? missionMedia?.poster : undefined) || eventAsset.poster || eventAsset.fallbackPoster,
    fallbackSrc: missionMedia?.fallback ? missionMedia.fallback.src : eventAsset.fallbackSrc,
    fallbackPoster: missionMedia?.fallback ? missionMedia.fallback.poster : eventAsset.fallbackPoster,
    assetId: missionMedia?.assetId || eventAsset.assetId,
    cue: snapshot.storyMission.visualCue || eventAsset.cue || node.mediaCue || node.action,
  }
  if (snapshot.storyMission && missionMediaReady && missionMedia?.src) return {
    src: missionMedia.src,
    poster: missionMedia.poster,
    fallbackSrc: missionMedia.fallback ? missionMedia.fallback.src : nodeAsset.fallbackSrc,
    fallbackPoster: missionMedia.fallback ? missionMedia.fallback.poster : nodeAsset.fallbackPoster,
    assetId: missionMedia.assetId,
    cue: snapshot.storyMission.visualCue || node.mediaCue || node.action,
  }
  if (explicitNodeSrc) return {
    src: explicitNodeSrc,
    poster: node.poster || node.media?.poster || nodeAsset.poster || nodeAsset.fallbackPoster,
    fallbackSrc: node.media?.fallback ? node.media.fallback.src : nodeAsset.fallbackSrc,
    fallbackPoster: node.media?.fallback ? node.media.fallback.poster : nodeAsset.fallbackPoster,
    assetId: node.media?.assetId || nodeAsset.assetId,
    cue: node.mediaCue || node.action,
  }
  if (guidedCharacter?.video) return {
    src: guidedCharacter.video,
    poster: guidedCharacter.portrait,
    fallbackSrc: nodeAsset.fallbackSrc,
    fallbackPoster: nodeAsset.fallbackPoster,
    assetId: `CHAR-${guidedCharacter.id}-guided-scene`,
    cue: node.mediaCue || node.action || `${guidedCharacter.name}停下手边的事，正在等你开口`,
  }
  if (node.cinematic) return {
    src: node.cinematic,
    poster: node.poster || node.media?.poster || nodeAsset.poster || nodeAsset.fallbackPoster,
    fallbackSrc: node.media?.fallback?.src || nodeAsset.fallbackSrc,
    fallbackPoster: node.media?.fallback?.poster || nodeAsset.fallbackPoster,
    assetId: nodeAsset.assetId,
    cue: node.mediaCue || node.action,
  }
  return {
    src: nodeAsset.src || nodeAsset.fallbackSrc,
    poster: nodeAsset.poster || nodeAsset.fallbackPoster,
    fallbackSrc: node.media?.fallback?.src || nodeAsset.fallbackSrc,
    fallbackPoster: node.media?.fallback?.poster || nodeAsset.fallbackPoster,
    assetId: nodeAsset.assetId,
    cue: node.mediaCue || node.action || nodeAsset.cue,
  }
}

function Game({ view, onView, onRestart }: { view: View; onView: (view: View) => void; onRestart: () => Promise<void> }) {
  const { snapshot, node, characters } = view
  const [chatCharacter, setChatCharacter] = useState<Character | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [receipt, setReceipt] = useState<Receipt | null>(null)
  const [cinematic, setCinematic] = useState<string | null>(node.cinematic || null)
  const [cinematicTitle, setCinematicTitle] = useState(node.title || '新的故事开始')
  const [cinematicPreviewedSrc, setCinematicPreviewedSrc] = useState<string | null>(null)
  const autoOpenedChatRef = useRef<string | null>(null)
  const perspectiveId = snapshot.player.perspectiveCharacterId || characters.find(character => character.isPlayerPerspective)?.id
  const perspectiveCharacter = characters.find(character => character.id === perspectiveId)
  const nodeCharacter = characters.find(character => character.id === (node.speakerCharacterId || node.characterId))
  const activeCharacter = nodeCharacter?.id === perspectiveId ? undefined : nodeCharacter
  const narrationBeats = useMemo(() => buildNarrationBeats(node.text || '', node.textBeats), [node.text, node.textBeats])
  const presentationKey = `${snapshot.nodeId}:${node.title}:${narrationBeats.join('\u241e')}`
  // A cinematic is an authored reading beat, not merely a visual layer. Keep
  // narration at its first frame until the one-shot film naturally ends (or
  // the viewer explicitly skips it), then begin the typewriter from character
  // one. This prevents the passage from completing unseen behind the overlay.
  const typewriter = useTypewriter(narrationBeats, presentationKey, !!cinematic)
  const storyOverlayPhase = useStoryOverlayPhase(typewriter.readyForChoices, presentationKey)
  const guidedCandidateId = resolveGuidedCharacterId(view)
  const guidedCharacterId = guidedCandidateId && guidedCandidateId !== perspectiveId && characters.some(character => character.id === guidedCandidateId) ? guidedCandidateId : null
  const sceneMedia = resolveSceneMedia(view, guidedCharacterId)
  const pendingChat = resolvePendingChat(view)
  const pendingAutoOpen = !!pendingChat && (typeof pendingChat !== 'object' || (pendingChat.autoOpen !== false && pendingChat.status !== 'completed'))
  const pendingToken = typeof pendingChat === 'object' && pendingChat?.id ? pendingChat.id : `${snapshot.runId}:${snapshot.nodeId}:${guidedCharacterId}`
  const availableChoices = node.choices.filter(choice => (choice.characterId || choice.targetCharacterId) !== perspectiveId)
  useEffect(() => {
    if (!typewriter.readyForChoices || !guidedCharacterId || !pendingAutoOpen || autoOpenedChatRef.current === pendingToken) return
    const target = characters.find(character => character.id === guidedCharacterId)
    if (!target) return
    autoOpenedChatRef.current = pendingToken
    setChatCharacter(target)
  }, [characters, guidedCharacterId, pendingAutoOpen, pendingToken, typewriter.readyForChoices])
  const choose = async (choice: Choice) => {
    if (!typewriter.readyForChoices) return
    unlockAudioIntent()
    setBusy(true); setError('')
    try {
      const result = await api<View & { receipt: Receipt }>(`/api/runs/${snapshot.runId}/choices`, {
        method: 'POST', body: JSON.stringify({ choiceId: choice.id, characterId: choice.characterId || choice.targetCharacterId, revision: snapshot.revision })
      })
      setReceipt(result.receipt); setTimeout(() => setReceipt(null), 3300)
      onView(result)
      if (result.node.cinematic) { setCinematicPreviewedSrc(null); setCinematicTitle(result.node.title || '新的故事开始'); setCinematic(result.node.cinematic) }
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
  const directStory = async () => {
    unlockAudioIntent()
    setBusy(true); setError('')
    try {
      const result = await api<View & { receipt: Receipt }>(`/api/runs/${snapshot.runId}/story-director`, {
        method: 'POST', body: JSON.stringify({ revision: snapshot.revision })
      })
      setReceipt(result.receipt); setTimeout(() => setReceipt(null), 4300); onView(result)
      if (result.receipt.kind === 'story-event' && result.receipt.mission?.media?.src) {
        setCinematicPreviewedSrc(null)
        setCinematicTitle(result.receipt.mission.title || result.receipt.title || '新的主任务')
        setCinematic(result.receipt.mission.media.src)
      }
    } catch (reason) { setError((reason as Error).message) }
    finally { setBusy(false) }
  }
  const resolveMission = async (outcome: 'completed' | 'declined') => {
    if (!snapshot.storyMission) return
    unlockAudioIntent()
    setBusy(true); setError('')
    try {
      const result = await api<View & { receipt: Receipt }>(`/api/runs/${snapshot.runId}/story-missions/${snapshot.storyMission.id}/resolve`, {
        method: 'POST', body: JSON.stringify({ revision: snapshot.revision, outcome, evidence: outcome === 'completed' ? '玩家确认已完成当前可执行任务' : '玩家使用了事件模板提供的退出路径' })
      })
      setReceipt(result.receipt); setTimeout(() => setReceipt(null), 3300); onView(result)
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
  const guidedInteractionDone = typeof pendingChat === 'object' && pendingChat?.status === 'completed'
  const guidedMemoryDone = !!guidedCharacterId && snapshot.echoMemories.some(memory => memory.characterId === guidedCharacterId)
  const interactionHasMemory = guidedCharacterId ? guidedMemoryDone : memoriesDone
  const requiredInteractionDone = guidedInteractionDone || guidedMemoryDone
  const directorAvailable = node.allowDirector === true || (snapshot.storyArc.phase === 'late' && !node.isEnding)
  return (
    <main className="game-shell game-shell--immersive">
      <header className="game-topbar">
        <div><span>心动之旅</span><small>{node.chapter}</small></div>
        <div className="game-progress"><i style={{ width: `${PROGRESS[snapshot.nodeId] || 0}%` }} /></div>
        <button className="signal-button" aria-label="关系状态"><HeartMark small /><span>{snapshot.flags.heat + snapshot.echoMemories.length}</span></button>
      </header>
      <section className="scene-stage">
        <SceneMedia src={sceneMedia.src} poster={sceneMedia.poster} fallbackSrc={sceneMedia.fallbackSrc} fallbackPoster={sceneMedia.fallbackPoster} assetId={sceneMedia.assetId} cue={sceneMedia.cue} active={!chatCharacter && !cinematic} firstPassConsumed={cinematicPreviewedSrc === sceneMedia.src} />
        <div className="scene-atmosphere" />
        <div className="scene-time"><span>{node.eyebrow}</span><i /></div>
        {activeCharacter && <div className="scene-character-tag" style={{ '--accent': activeCharacter.accent } as React.CSSProperties}><b>{activeCharacter.name}</b><span>{activeCharacter.mbti} · {activeCharacter.tagline}</span></div>}
        {!activeCharacter && perspectiveCharacter && <div className="scene-pov-tag"><span>你的视角</span><b>{perspectiveCharacter.name}正在经历这一幕</b></div>}
      </section>
      <div className="story-overlay-zone">
      <section className={`story-card story-card--${storyOverlayPhase}`} data-story-phase={storyOverlayPhase}>
        {storyOverlayPhase !== 'interaction' && <div className="story-narration-layer" data-story-layer="narration">
          <div className="story-card__chapter"><span>{node.speaker}</span><i /></div>
          <button className="story-narration" type="button" onClick={typewriter.reveal} aria-label={`${node.title}。第${typewriter.beatIndex + 1}段，共${typewriter.beatCount}段。${typewriter.text}。${typewriter.complete ? '轻触继续。' : '轻触补全本段。'}`}>
            <h1>{node.title}</h1>
            <p data-beat={`${typewriter.beatIndex + 1}/${typewriter.beatCount}`}>{typewriter.text}<i className={typewriter.complete ? 'typewriter-cursor complete' : 'typewriter-cursor'} aria-hidden="true" /></p>
            <small className="story-continue-hint">{!typewriter.complete ? `轻触补全本段 · ${typewriter.beatIndex + 1}/${typewriter.beatCount}` : typewriter.isLastBeat ? '再轻触一次，进入选择' : `轻触继续下一段 · ${typewriter.beatIndex + 1}/${typewriter.beatCount}`}</small>
          </button>
        </div>}
        {storyOverlayPhase === 'interaction' && <div className="story-reveal" data-story-layer="interaction">
          {node.gameBrief && <GameBrief brief={node.gameBrief} />}
          {snapshot.storyMission ? <DirectorMission mission={snapshot.storyMission} characters={characters} busy={busy} onResolve={resolveMission} /> : directorAvailable && memoriesDone && <button className="director-trigger" disabled={busy} onClick={directStory}><span><b>让剧情导演读取此刻的关系证据</b><small>从已研究的恋综事件库中激活下一项主任务</small></span><i>{busy ? '…' : '↗'}</i></button>}
          {(node.requiresMemory || node.requiresGuidedInteraction) && <div className={`link-proof ${(node.requiresGuidedInteraction ? requiredInteractionDone : eventDone) ? 'done' : ''} ${guidedCharacterId && !requiredInteractionDone ? 'guided' : ''}`}>
            <span>{node.requiresGuidedInteraction && requiredInteractionDone ? '✓' : eventDone ? '✓' : interactionHasMemory ? '02' : '01'}</span><div><b>{node.requiresGuidedInteraction && requiredInteractionDone ? '破冰对话已完成，现在轮到你决定怎样邀请' : eventDone ? '专属事件已经进入正片' : interactionHasMemory ? '继续交流，让对方作出一个具体选择' : guidedCharacterId ? `剧情正在等你与${characters.find(character => character.id === guidedCharacterId)?.name || '指定嘉宾'}开口` : '先完成一次 1 对 1 交流'}</b><small>{node.requiresGuidedInteraction && requiredInteractionDone ? '对方已经记住你们的第一次真实来回' : eventDone ? snapshot.eventLedger[snapshot.eventLedger.length - 1]?.label : interactionHasMemory ? '角色会依据人物卡决定是否交出线索或邀约' : guidedCharacterId ? '下方对应头像已点亮“1”，先从自我介绍和寒暄开始' : '从一声招呼开始，不用一上来就谈任务'}</small></div>
          </div>}
          {!!availableChoices.length && <section className={`choice-section ${node.characterChoice ? 'choice-section--cast' : ''}`} aria-label="剧情选择">
            <div className="choice-section__heading"><span>{node.characterChoice ? '今晚，你想把心动短信发给谁？' : '这一刻，你准备怎么做？'}</span><small>你的选择会改变接下来的相处</small></div>
            <div className={`choice-stack ${node.characterChoice ? 'character-choices' : ''} ${snapshot.nodeId === 'icebreaker-choice' ? 'choice-stack--icebreaker' : ''}`}>
              {availableChoices.map((choice, index) => {
                const choiceCharacterId = choice.characterId || choice.targetCharacterId
                const character = choiceCharacterId ? characters.find(c => c.id === choiceCharacterId) : null
                return (
                  <button key={choice.id} disabled={busy || (!!node.requiresGuidedInteraction && !requiredInteractionDone) || (!!node.requiresMemory && !memoriesDone) || (!!node.requiresEvent && !eventDone)} onClick={() => choose(choice)} style={character ? { '--accent': character.accent } as React.CSSProperties : undefined}>
                    {snapshot.nodeId === 'icebreaker-choice' && character ? <>
                      <span className="icebreaker-card__top"><em>三分钟生活观察卡</em><i>{String(index + 1).padStart(2, '0')}</i></span>
                      <span className="icebreaker-card__person"><img src={character.portrait} alt="" /><span><b>{character.name}<em>{character.mbti}</em></b><small>{character.tagline}</small></span></span>
                      <span className="icebreaker-card__action"><em>你要做什么</em><b>{choice.label}</b></span>
                      <span className="icebreaker-card__question"><em>三分钟内，问到这件小事</em><span>{choice.hint || character.independentInterest}</span></span>
                      <i className="icebreaker-card__arrow">→</i>
                    </> : <>
                      {character && <img src={character.portrait} alt="" />}
                      <span className="choice-index">{String(index + 1).padStart(2, '0')}</span>
                      <span className="choice-copy"><b>{choice.label}</b><small>{choice.hint}</small></span><i>→</i>
                    </>}
                  </button>
                )
              })}
            </div>
          </section>}
          {node.isEnding && <div className="ending-proof"><span>首个联通闭环已完成</span><p>你的文字选择进入角色记忆，并在剧情回声中触发了新的表达。</p><button disabled={busy} onClick={restart}>{busy ? '正在重启心动信号…' : '重新开始一段旅程'}</button></div>}
          {error && <p className="error-note">{error}</p>}
        </div>}
      </section>
      </div>
      <CharacterDock characters={characters} snapshot={snapshot} guidedCharacterId={typewriter.readyForChoices ? guidedCharacterId : null} guidedComplete={node.requiresGuidedInteraction ? requiredInteractionDone : node.requiresEvent ? eventDone : memoriesDone} onOpen={setChatCharacter} />
      {chatCharacter && chatCharacter.id !== perspectiveId && <ChatSheet key={chatCharacter.id} character={chatCharacter} characters={characters} snapshot={snapshot} embeddedOpener={view.chatOpeners?.[chatCharacter.id] || snapshot.chatOpeners?.[chatCharacter.id]} onClose={() => setChatCharacter(null)} onSend={send} busy={busy} />}
      {cinematic && <Cinematic src={cinematic} title={cinematicTitle} onDone={() => { setCinematicPreviewedSrc(cinematic); setCinematic(null) }} />}
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
      .then(data => { setCharacters(data.characters); setView(new URLSearchParams(location.search).get('intro') === '1' ? null : data.view) })
      .catch(error => setAuthError(error.message))
      .finally(() => setLoading(false))
  }, [])
  const cast = useMemo(() => view?.characters || characters, [view, characters])
  const start = async (mbti: string, perspectiveCharacterId?: string) => {
    setBusy(true)
    try { setView(await api<View>('/api/runs', { method: 'POST', body: JSON.stringify({ mbti, perspectiveCharacterId }) })) }
    catch (error) { setAuthError((error as Error).message) }
    finally { setBusy(false) }
  }
  if (loading) return <Loading />
  if (authError) return <LoginGate message={authError} />
  if (!view) return <Landing characters={cast} onStart={start} busy={busy} />
  return <Game view={view} onView={setView} onRestart={() => start(view.snapshot.player.mbti, view.snapshot.player.perspectiveCharacterId)} />
}
