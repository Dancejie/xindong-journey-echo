(function () {
  'use strict';

  var STORAGE_KEY = 'heart-journey-minitool-v1';
  var MBTIS = ['INFP','ENFP','INFJ','ENFJ','INTJ','ENTJ','INTP','ENTP','ISFP','ESFP','ISFJ','ESFJ','ISTP','ESTP','ISTJ','ESTJ'];
  var PROGRESS = { arrival: 8, first: 30, private: 55, letter: 78, callback: 100 };
  var CHARACTERS = [
    {id:'shenmo',name:'沈墨',mbti:'INTJ',tagline:'温柔的理想主义者',accent:'#7187c9',mask:'礼貌、克制，习惯先观察再靠近。',fear:'被热烈地选择，却从未真正被理解。',voice:'短句、留白、准确',seed:'三年前他在一次告白中沉默太久，从此把想说的话先写在纸上。',prompts:['你刚才为什么一直看海？','如果只能说一句真话呢？','我不会逼你现在回答。']},
    {id:'linyu',name:'林屿',mbti:'ISFJ',tagline:'安静的洞察者',accent:'#9d83bb',mask:'总能先发现谁需要一杯水。',fear:'自己的照顾被当成理所当然。',voice:'温和、具体，先回应感受',seed:'他记得每个人第一次见面时喝的饮料，却很少有人问他想喝什么。',prompts:['今天也有人照顾你吗？','你记住了我的什么？','这次换我听你说。']},
    {id:'chengye',name:'程野',mbti:'ESTP',tagline:'机智的挑战者',accent:'#506fb1',mask:'玩笑开得快，接住尴尬也很快。',fear:'安静下来以后，没有人愿意留下。',voice:'轻快、直接、带一点反问',seed:'他把一次失败的约会讲成笑话，只有自己知道那天等到了凌晨。',prompts:['你是不是只会用玩笑躲开？','敢不敢认真回答一次？','我留下，不是因为无聊。']},
    {id:'guyan',name:'顾言',mbti:'INTP',tagline:'天生的精准观察者',accent:'#63a786',mask:'像在旁观实验，其实比谁都在意变量。',fear:'表达不够及时，关系就已经被别人定义。',voice:'先拆解问题，再给诚实结论',seed:'他保留着一张没有寄出的明信片，因为找不到足够准确的措辞。',prompts:['别分析，先告诉我你的感觉。','你觉得我们是什么变量？','不准确也可以说。']},
    {id:'jiangwan',name:'江晚',mbti:'INFJ',tagline:'安静的洞察者',accent:'#9a7cca',mask:'不抢话，却常常看见没被说出口的那层。',fear:'理解所有人，最后却没人看见她。',voice:'柔和，追问真正的需要',seed:'她曾替朋友写过很多告别信，自己的那封一直停在第一行。',prompts:['你刚才是不是看懂我了？','你希望谁先看见你？','我想听你的第一行。']},
    {id:'jiangmi',name:'姜米',mbti:'ENFP',tagline:'热烈的追梦者',accent:'#e7758f',mask:'把每次相遇都当成会发光的新故事。',fear:'热烈退潮后，自己只剩下吵闹。',voice:'有画面感、真诚、反应快',seed:'她每次旅行都会给未来的自己录一段语音，唯独不敢回听上一段。',prompts:['你刚才的笑是真的吗？','我们去做一件没计划的事？','安静的时候我也想认识你。']},
    {id:'sunnian',name:'苏念',mbti:'ESFJ',tagline:'温暖的守护者',accent:'#d9904a',mask:'让所有人都舒服，是她进入陌生场合的本能。',fear:'一旦停止有用，就失去被爱的资格。',voice:'明亮、周到，会给具体回应',seed:'她能办好所有人的生日，却连续两年假装忘了自己的。',prompts:['如果今天不用照顾任何人呢？','你真正想收到什么？','我记得你的需要。']},
    {id:'chensu',name:'陈叙',mbti:'ISTP',tagline:'沉默的行动派',accent:'#c98a56',mask:'话少，但总在事情失控前伸手。',fear:'自己不擅长解释，最终被误会成不在乎。',voice:'简短、朴素，用行动回应',seed:'他修好过前任留下的旧相机，却始终没有洗出最后一卷胶片。',prompts:['你不说，但你会怎么做？','那卷胶片为什么没洗？','沉默也可以一起待着。']}
  ];
  var NODES = {
    arrival:{chapter:'DAY 1 · 初见',time:'心动小屋 / 18:47',title:'海风替你推开了门',speaker:'旁白',text:'八个人已经到了。你会先让谁看见你，也会决定谁在今晚记住你。',motion:'arrival',cinematic:'arrival',choices:[
      {id:'arrive-open',label:'先走进人群',hint:'热度上升，姜米和程野会先注意你',next:'first',heat:2,aff:{jiangmi:2,chengye:2}},
      {id:'arrive-help',label:'接过苏念手里的杯子',hint:'温柔会被记住',next:'first',clarity:1,aff:{sunnian:3,linyu:1}},
      {id:'arrive-observe',label:'在门边看十秒',hint:'你会读到两道没有移开的目光',next:'first',clarity:2,aff:{shenmo:2,jiangwan:2}}
    ]},
    first:{chapter:'DAY 1 · 第一印象',time:'露台晚宴 / 19:12',title:'有人把座位留在了身边',speaker:'姜米',character:'jiangmi',text:'“我刚才猜你会坐最远的位置。”\n她把椅子向外拉了半步，“结果你比我想得更勇敢。”',choices:[
      {id:'answer-playful',label:'“那你猜错的代价是什么？”',hint:'把试探变成暧昧',next:'private',heat:2,aff:{jiangmi:3}},
      {id:'answer-honest',label:'“其实我只是怕错过。”',hint:'坦白会提高自我清晰度',next:'private',clarity:2,aff:{jiangwan:1,linyu:1}},
      {id:'answer-return',label:'“那你为什么给我留位置？”',hint:'把镜头交回给她',next:'private',clarity:1,aff:{jiangmi:2}}
    ]},
    private:{chapter:'DAY 1 · 私聊时间',time:'自由交流 / 20:06',title:'镜头之外，才是关系开始的地方',speaker:'节目提示',text:'现在可以进入任意嘉宾的 1 对 1 房间。你说过的话会进入对方的独立记忆，并在后续剧情里被重新提起。至少完成一次私聊，再继续。',motion:'arrival',requiresMemory:true,choices:[{id:'continue-letter',label:'写下匿名心动信',hint:'把私聊留下的记忆带进正片',next:'letter',heat:1}]},
    letter:{chapter:'DAY 1 · 匿名信',time:'心动信箱 / 22:30',title:'没有署名，但每句话都有来处',speaker:'旁白',text:'你只能把第一封信交给一个人。今晚的私聊记忆，会改变对方读信后的回应。',motion:'letter',cinematic:'letter',characterChoice:true,choices:[]},
    callback:{chapter:'DAY 2 · 回声',time:'清晨海边 / 07:18',title:'有人记得你没有说完的那句话',speaker:'回声',text:'天亮以后，昨夜的选择没有消失。它已经变成一个人看向你的方式。',ending:true,choices:[]}
  };

  var app = document.getElementById('app');
  var state = readState();
  var ui = { mbti:'INFP', chat:null, typing:false, cinematic:null, toast:null };

  function freshState(mbti) {
    var affection = {}, trust = {};
    CHARACTERS.forEach(function(c){ affection[c.id]=0; trust[c.id]=0; });
    return {version:1,node:'arrival',mbti:mbti||'INFP',revision:0,heat:0,clarity:0,affection:affection,trust:trust,memories:[],choices:[],focus:null,recipient:null};
  }
  function readState() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      return parsed && parsed.version===1 ? parsed : null;
    } catch (ignore) { return null; }
  }
  function saveState() {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (ignore) {}
  }
  function esc(value) {
    return String(value==null?'':value).replace(/[&<>'"]/g,function(ch){return {'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch];});
  }
  function charById(id) { return CHARACTERS.filter(function(c){return c.id===id;})[0] || null; }
  function portrait(c) { return './assets/media/portraits/'+c.id+'.jpg'; }
  function motion(id) { return './assets/media/motion/'+id+'.webp'; }
  function memoriesFor(id) { return state ? state.memories.filter(function(m){return m.characterId===id;}) : []; }
  function mediaName(node) { return node.motion || node.character || 'arrival'; }
  function later(fn, ms) { return window.setTimeout(fn, ms); }

  function render() {
    ['chat-layer','cinematic-layer','toast-layer'].forEach(function(id){var old=document.getElementById(id);if(old)old.remove();});
    if (!state) renderLanding(); else renderGame();
    bindCommon();
    if (ui.chat) renderChat();
    if (ui.cinematic) renderCinematic();
    if (ui.toast) renderToast();
  }
  function castMarkup() {
    return CHARACTERS.map(function(c){return '<article class="cast-item" style="--accent:'+c.accent+'"><div class="cast-photo"><img src="'+portrait(c)+'" alt="'+c.name+'"></div><b>'+c.mbti+'</b><span>'+c.name+'</span></article>';}).join('');
  }
  function renderLanding() {
    app.innerHTML = '<main class="shell landing"><div class="landing-bg"><img class="media" src="'+motion('arrival')+'" alt=""></div><header class="topbar"><span>全球首档 MBTI 沉浸式恋爱实验</span><span class="live"><i></i>DAY 1</span></header><section class="hero"><p class="hero-overline">选择一种靠近的方式</p><div class="hero-title"><h1>心动之旅</h1><span class="heart">♡</span></div><p class="hero-sub">MBTI · Journey of Heart</p><p class="hero-copy">没有人是被“拯救”的。<br>每个人都带着自己的软处走进来。</p></section><section class="cast">'+castMarkup()+'</section><section class="start-card glass"><div class="start-head"><b>你的观察视角</b><small>不是标签，只是故事的起点</small></div><div class="mbtis">'+MBTIS.map(function(m){return '<button class="'+(m===ui.mbti?'active':'')+'" data-mbti="'+m+'">'+m+'</button>';}).join('')+'</div><button class="primary" data-action="start">以我的方式进入小屋　→</button><p class="fineprint">离线角色 Agent · 独立本地记忆 · 选择回流剧情</p></section></main>';
  }
  function projectedNode() {
    var node = NODES[state.node];
    if (state.node!=='callback') return node;
    var c = charById(state.recipient || state.focus);
    if (!c) return node;
    var memories = memoriesFor(c.id);
    var last = memories[memories.length-1];
    return {chapter:node.chapter,time:node.time,title:node.title,speaker:c.name,character:c.id,ending:true,choices:[],text:last?'“昨晚你说『'+last.playerText.slice(0,32)+'』的时候，我其实记住了。”\n'+c.name+'没有替你定义答案，只把并肩的位置留了出来。':c.name+'在晨光里拆开信，抬头时没有躲开你的目光。关系没有被一次选择决定，但它已经开始。'};
  }
  function choiceMarkup(node) {
    var choices = node.characterChoice ? CHARACTERS.map(function(c){return {id:'letter-'+c.id,characterId:c.id,label:'写给 '+c.name,hint:c.mbti+' · '+c.tagline};}) : node.choices;
    return choices.map(function(choice,index){var c=choice.characterId?charById(choice.characterId):null;return '<button class="choice '+(c?'has-photo':'')+'" data-choice="'+choice.id+'" '+(node.requiresMemory&&!state.memories.length?'disabled':'')+'>'+(c?'<img class="choice-photo" src="'+portrait(c)+'" alt="">':'<span class="choice-index">'+String(index+1).padStart(2,'0')+'</span>')+'<span class="choice-copy"><b>'+esc(choice.label)+'</b><small>'+esc(choice.hint)+'</small></span><span class="choice-arrow">→</span></button>';}).join('');
  }
  function dockMarkup() {
    return '<nav class="dock"><div class="dock-label"><b>心动小屋 · 1 对 1</b><span>点击立绘开始即时交流</span></div><div class="dock-scroll">'+CHARACTERS.map(function(c){var count=memoriesFor(c.id).length;return '<button class="avatar" data-chat="'+c.id+'" style="--accent:'+c.accent+'"><span class="avatar-photo"><img src="'+portrait(c)+'" alt="">'+(count?'<i>'+count+'</i>':'')+'</span><b>'+c.name+'</b><small>'+c.mbti+'</small></button>';}).join('')+'</div></nav>';
  }
  function renderGame() {
    var node=projectedNode(), active=charById(node.character), scene=active?active.id:mediaName(node), linked=state.memories.length>0;
    app.innerHTML='<main class="shell game"><header class="game-head"><div class="brand"><b>心动之旅</b><small>'+node.chapter+'</small></div><div class="progress"><i style="width:'+(PROGRESS[state.node]||0)+'%"></i></div><button class="signal">♡ '+(state.heat+state.memories.length)+'</button></header><section class="stage"><img class="media" src="'+motion(scene)+'" alt="'+(active?active.name:'心动小屋动态场景')+'"><div class="scene-time"><span>'+node.time+'</span><i></i></div>'+(active?'<div class="character-tag" style="--accent:'+active.accent+'"><b>'+active.name+'</b><span>'+active.mbti+' · '+active.tagline+'</span></div>':'')+'</section><section class="story"><div class="speaker"><span>'+node.speaker+'</span><i></i></div><h1>'+node.title+'</h1><p class="story-text">'+esc(node.text)+'</p>'+(node.requiresMemory?'<div class="proof '+(linked?'done':'')+'"><span>'+(linked?'✓':'01')+'</span><div><b>'+(linked?'私聊记忆已经接入正片':'先完成一次 1 对 1 交流')+'</b><small>'+(linked?state.memories.length+' 段记忆可被后续剧情回调':'点击下方任意嘉宾立绘进入私聊')+'</small></div></div>':'')+'<div class="choices">'+choiceMarkup(node)+'</div>'+(node.ending?'<div class="ending"><b>首个联通闭环已完成</b><p>你的文字进入角色独立记忆，并在剧情回声中触发新的表达。</p><button data-action="restart">重新开始一段旅程</button></div>':'')+'</section>'+dockMarkup()+'</main>';
  }
  function bindCommon() {
    Array.prototype.forEach.call(document.querySelectorAll('[data-mbti]'),function(el){el.addEventListener('click',function(){ui.mbti=el.getAttribute('data-mbti');render();});});
    var start=document.querySelector('[data-action="start"]'); if(start)start.addEventListener('click',function(){state=freshState(ui.mbti);saveState();ui.cinematic='arrival';render();});
    var restart=document.querySelector('[data-action="restart"]'); if(restart)restart.addEventListener('click',function(){state=null;ui.chat=null;ui.cinematic=null;try{localStorage.removeItem(STORAGE_KEY);}catch(ignore){}render();});
    Array.prototype.forEach.call(document.querySelectorAll('[data-chat]'),function(el){el.addEventListener('click',function(){ui.chat=el.getAttribute('data-chat');render();});});
    Array.prototype.forEach.call(document.querySelectorAll('[data-choice]'),function(el){el.addEventListener('click',function(){choose(el.getAttribute('data-choice'));});});
  }
  function choose(id) {
    var node=NODES[state.node];
    if(node.requiresMemory&&!state.memories.length){showToast('先留下共同记忆','和任意嘉宾完成一次 1 对 1 交流');return;}
    var choice=null;
    if(node.characterChoice){var recipient=id.replace('letter-','');if(!charById(recipient))return;state.recipient=recipient;state.focus=recipient;state.affection[recipient]+=5;choice={id:id,next:'callback'};}
    else {choice=node.choices.filter(function(item){return item.id===id;})[0];if(!choice)return;if(choice.heat)state.heat+=choice.heat;if(choice.clarity)state.clarity+=choice.clarity;if(choice.aff)Object.keys(choice.aff).forEach(function(k){state.affection[k]+=choice.aff[k];});}
    state.choices.push({id:id,revision:state.revision+1});state.node=choice.next;state.revision+=1;saveState();
    if(NODES[state.node].cinematic)ui.cinematic=NODES[state.node].cinematic;
    showToast('选择已经写入故事','文字剧情 · 角色记忆 · 动态影像已同步');render();
  }
  function renderChat() {
    var c=charById(ui.chat);if(!c)return;var memories=memoriesFor(c.id);
    var layer=document.createElement('div');layer.className='backdrop';layer.id='chat-layer';layer.innerHTML='<section class="chat" style="--accent:'+c.accent+'"><div class="chat-hero"><div class="chat-media"><img class="chat-media-blur" src="'+motion(c.id)+'" alt=""><img class="chat-media-subject" src="'+motion(c.id)+'" alt="'+c.name+'动态立绘"></div><button class="close" data-close-chat aria-label="关闭">×</button><div class="identity"><em>'+c.mbti+'</em><h2>'+c.name+'</h2><p>'+c.tagline+'</p></div><div class="memory-badge">♡ '+(memories.length?memories.length+' 段共同记忆':'从这一句开始')+'</div></div><div class="chat-body"><div class="agent-note"><b>只对你开放的那一面</b><p>'+c.mask+'</p></div><div class="messages" id="message-stream">'+(!memories.length?'<div class="message"><b>'+c.name+'</b><p>这里没有其他人的镜头。你可以不用急着表现得正确。</p></div>':'')+memories.slice(-5).map(function(m){return '<div class="message player"><p>'+esc(m.playerText)+'</p></div><div class="message"><b>'+c.name+'</b><p>'+esc(m.agentReply)+'</p><small>已写入你们的独立记忆 · 好感 '+(m.affectionDelta?'+':'')+m.affectionDelta+' · 信任 '+(m.trustDelta?'+':'')+m.trustDelta+'</small></div>';}).join('')+(ui.typing?'<div class="message typing"><i></i><i></i><i></i></div>':'')+'</div><div class="chips">'+c.prompts.map(function(p){return '<button data-prompt="'+esc(p)+'">'+esc(p)+'</button>';}).join('')+'</div><form class="composer" id="composer"><textarea id="draft" maxlength="240" placeholder="只对'+c.name+'说…"></textarea><button id="send" type="submit" disabled>↗</button></form><p class="agent-boundary">包内即时角色 Agent · 记忆仅保存在本机 · 规则裁决剧情边界</p></div></section>';
    document.body.appendChild(layer);
    var close=function(){ui.chat=null;ui.typing=false;layer.remove();};
    layer.querySelector('[data-close-chat]').addEventListener('click',close);
    layer.addEventListener('click',function(e){if(e.target===layer)close();});
    var draft=layer.querySelector('#draft'),send=layer.querySelector('#send'),form=layer.querySelector('#composer');
    draft.addEventListener('input',function(){send.disabled=!draft.value.trim()||ui.typing;});
    Array.prototype.forEach.call(layer.querySelectorAll('[data-prompt]'),function(el){el.addEventListener('click',function(){draft.value=el.getAttribute('data-prompt');send.disabled=false;draft.focus();});});
    form.addEventListener('submit',function(e){e.preventDefault();var text=draft.value.trim();if(!text||ui.typing)return;draft.value='';send.disabled=true;submitMessage(c,text);});
    var stream=layer.querySelector('#message-stream');stream.scrollTop=stream.scrollHeight;
  }
  function classify(text) {
    if(/滚|闭嘴|废物|必须喜欢|逼你|操控/.test(text))return {intent:'boundary',aff:0,trust:0};
    if(/喜欢|心动|留下|想你|约会|靠近/.test(text))return {intent:'flirt',aff:2,trust:1};
    if(/为什么|告诉我|想听|怎么想|感觉|秘密/.test(text))return {intent:'listen',aff:1,trust:2};
    if(/敢不敢|挑战|认真|别躲|真话/.test(text))return {intent:'challenge',aff:1,trust:1};
    return {intent:'presence',aff:1,trust:1};
  }
  function responseFor(c,text,intent) {
    var head=text.length>28?text.slice(0,28)+'…':text;
    var replies={
      boundary:{shenmo:'我听见了，但逼迫不会让答案更真。我们可以停在这里。',linyu:'我愿意听，但不接受用伤害换亲密。先照顾好边界。',chengye:'挑战可以，羞辱不行。这条线我说得很清楚。',guyan:'这个前提越过边界了，所以我不继续推演。',jiangwan:'我不会替冒犯寻找浪漫解释。我们先停一下。',jiangmi:'热烈不是没有底线。这样的话，我不会笑着接住。',sunnian:'照顾你的感受，不代表我要接受伤害。',chensu:'这句越界了。停在这里。'},
      flirt:{shenmo:'“'+head+'”我记住了。靠近可以慢一点，但不用撤回。',linyu:'听见你这样说，我也想把自己的需要放到你面前一次。',chengye:'这算直球？行，我不躲。下次把“想”变成一起去做。',guyan:'结论可能不够严谨：我愿意把你加入接下来的计划。',jiangwan:'你说的是靠近，也像是在问自己会不会被接住。我在听。',jiangmi:'那就别让这句话只停在今晚。我想认识热闹之外的你。',sunnian:'这一次我不急着照顾全场，只认真收下你的心意。',chensu:'知道了。明早海边，我给你留位置。'},
      listen:{shenmo:'你问到的不是答案，是我为什么沉默。因为我想确认你听见的是我，不是标签。',linyu:'谢谢你先问我。被记住很好，被询问真正想要什么更好。',chengye:'认真版只有一次：安静下来时，我也怕没人留下。',guyan:'感觉不是变量噪声。至少此刻，我不想把你的问题略过去。',jiangwan:'你在问我，其实也把“想被看见”交了出来。那句话我会保留。',jiangmi:'我会发光，也会累。你愿意听安静那一面，这很难得。',sunnian:'我真正想收到的，是一句不需要我先付出的关心。',chensu:'没洗那卷胶片，是因为结束比修东西难。现在说出来了。'},
      challenge:{shenmo:'真话是：我注意你比我表现出来的更早。说完了。',linyu:'那我认真回答：我不想永远只做照顾人的那一个。',chengye:'敢。真话是我开玩笑的时候，也在等你别走。',guyan:'不分析的版本：我在意，而且比预计得更快。',jiangwan:'第一行是：我也希望有人先看见我。',jiangmi:'认真答案：热闹散场以后，我仍然想和你坐在这里。',sunnian:'如果今天不用照顾任何人，我想先选一次自己。',chensu:'会怎么做？留下。不是为了证明什么。'},
      presence:{shenmo:'你不用把这句话变得更漂亮。我会按它原来的样子记住。',linyu:'嗯，我在。你慢慢说，不需要先照顾我的反应。',chengye:'这句我接到了。别急着补充，先让它在这儿待一会。',guyan:'信息不完整，但足够让我知道：你愿意把注意力留在这里。',jiangwan:'有些话不是为了立刻得到答案。它被听见，就已经开始改变关系。',jiangmi:'我喜欢这种没有剧本的一句。它让今晚突然变得很真。',sunnian:'谢谢你把这一刻交给我。这次我不急着把它安排妥当。',chensu:'嗯。记住了。你不用再解释一遍。'}
    };
    return replies[intent][c.id];
  }
  function submitMessage(c,text) {
    ui.typing=true;render();
    later(function(){var intent=classify(text),reply=responseFor(c,text,intent.intent);state.memories.push({id:String(Date.now()),characterId:c.id,playerText:text,agentReply:reply,intent:intent.intent,affectionDelta:intent.aff,trustDelta:intent.trust});state.affection[c.id]+=intent.aff;state.trust[c.id]+=intent.trust;state.focus=c.id;state.revision+=1;saveState();ui.typing=false;showToast(intent.intent==='boundary'?'边界已经保存':'一段真话被记住',c.name+' 的独立记忆已更新');render();},520);
  }
  function renderCinematic() {
    var id=ui.cinematic,layer=document.createElement('div');layer.className='cinematic';layer.id='cinematic-layer';layer.innerHTML='<img class="media" src="'+motion(id)+'" alt="动态过场"><div class="cinematic-copy"><span>HEART JOURNEY</span><b>'+(id==='letter'?'心意已经寄出':'选择已经发生')+'</b></div><button class="skip">继续</button>';document.body.appendChild(layer);var done=function(){ui.cinematic=null;layer.remove();};layer.querySelector('.skip').addEventListener('click',done);later(function(){if(ui.cinematic===id)done();},5100);
  }
  function showToast(title,detail) { ui.toast={title:title,detail:detail};later(function(){ui.toast=null;var old=document.getElementById('toast-layer');if(old)old.remove();},3000); }
  function renderToast() { var old=document.getElementById('toast-layer');if(old)old.remove();var toast=document.createElement('div');toast.className='toast';toast.id='toast-layer';toast.innerHTML='<b>♡　'+esc(ui.toast.title)+'</b><small>'+esc(ui.toast.detail)+'</small>';document.body.appendChild(toast); }

  window.addEventListener('resize',function(){ if(window.visualViewport){ document.documentElement.style.setProperty('--viewport-height',window.visualViewport.height+'px'); } });
  render();
}());
