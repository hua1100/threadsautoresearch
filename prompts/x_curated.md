# 策展內容

透過 Telegram 轉發的好內容會自動累積在這裡。
YouTube URL 會自動抓逐字稿。

<!-- 系統每次迴圈會自動 append 新的 Telegram 訊息 -->


## 2026-03-27 06:00 (via Telegram)
- Hi


## 2026-03-27 06:25 (via Telegram)
- Hi


## 2026-03-27 13:34 (via Telegram)
- 想像一個場景：
在家雙螢幕寫 Code 寫到一半 準備出門
把筆電改連手機熱點 拔掉電源 螢幕一蓋 直接丟進背包裡
就像手機放在口袋一樣 所有的 AI Agent 跟自動化腳本依然在背景瘋狂跑迴圈
到了咖啡廳 筆電一開 無縫接軌繼續工作
Apple Silicon 原廠其實寫死了一道物理枷鎖：沒插電蓋上螢幕 系統就強制休眠
為了解除這個封印 我在系統裡掛載了 Amphetamine 這個神器
多數人只拿它來防止螢幕變暗 這太浪費了
真正有價值的是它隱藏的 Power Protect 擴充腳本
它會直接繞過 Apple 的硬體限制 在底層覆寫 sudoers 權限
強行啟動 pmset -a disablesleep 1 的全域指令
讓你的 Mac 真正變成一台 24 小時不斷線的移動算力艙
把硬體的 Root 權限拿回來 跑起來就是爽
- 給 AI 時代的網站開發者的小技巧分享：
你可以用 HTTP Request Header 來判斷現在是人在看你的網站，還是 Agent 在幫他的主人看你的網站

如果 user-agent 是 Claude-User 或 accept 裡面有 text/markdown
那這個可能是 Claude Code 或 OpenClaw 或其他的 Agent 在網路上查東西查到你的網站了

利用這個小技巧，你可以針對 Agent 寫一些給他看的東西，而且用 Markdown 格式就好，省下了傳輸冗余 HTML 和 CSS 的時間，這些 Agent 讀取你網頁的速度會更快！

同時也可以用來分析是不是有越來越多 Agent 在看你的內容，某種另類的 SEO 分析（？
(要用的話要標注資料來源是zeabur創辦人）
- Gemini 這次更新真的強到沒朋友。
以後做 LINE Bot 不用再寫一堆判斷邏輯去 call API 了！

這次 03/17 的更新叫 Gemini Tool Combinations。
簡單說：你現在可以把 Google Search、Google Maps 跟自訂 Function 全部丟給 Gemini。

模型會自己決定：「喔，這題我要先去 Maps 找地點，再去 Search 查評論，最後再跑你的自訂邏輯。」

重點更新：
1️⃣ Tool Combinations：單次呼叫直接串接多個工具，模型自己當導演。
2️⃣ Maps Grounding：它真的看得懂地圖空間，不再只是文字復讀機。
3️⃣ Context Circulation：多輪對話的記憶流暢到不行。

原本要寫幾十行邏輯的「餐廳推薦機器人」，現在一句話就搞定。￼
- https://x.com/googledeepmind/status/2037190678883524716?s=52


## 2026-03-28 12:00 (via Telegram)
- 不要追求 AI 多快生出 code，要追求第一次就對

關於 Harness Engineering 的 First-pass Acceptance Rate — 怎麼讓 AI 第一次就給你期望的結果

最近為了做 autonomous agent 的研究，已經非常喜歡 Opus4.6 的表現，但我真的不想一直去注意 API key 的費用，所以就去研究了一下，我們現在用的 Claude Code setup-token 底下到底是怎麼運作的

——

秉持著研究的精神，既然「龍蝦」可以透過 Session Token 去使用 Claude 的訂閱，那它底下應該有一些運作原理蠻值得深入研究的

即使這會違反 TOS（服務條款），可能也值得看，因為在預算有限的情況下，還是需要一些必要的手段讓我們做更多實驗（在 AI 放大資本主義市場的循環下，不想讓工程變成只有有錢人才玩得起..）

底下的關鍵技術就是 libGDX 作者 Mario Zechner 的 badlogic/pi-mono 的 packages/ai

主要有四步：login 拿 token → 存起來 → 過期自動 refresh → 偵測到 sk-ant-oat 前綴就切 Bearer auth

Token/Storage/Refresh 三層完全分離
可以搬到任何環境跑

——

這不是要鼓勵去用，但如果是做實驗的話，這是目前預算控制最務實的方式

之前聊到連 web search 都可以偷渡 — CC 內建 web search，加上 -p flag 做 non-interactive 執行，原本要另外花錢買 Web Search API Key 的事，訂閱費裡就包了

好吧，一整個客家精神在用工具…

——

這次 survey 的過程本身讓我有一些 takeaway

Opus 4.6 第一次跑的時候，完全沒有找到怎麼讓 OAuth 變成類 API key 的用法，一直說「server 400、只有 Haiku 可以用」什麼的，至少 reject 我三次

既然我都知道 pi-mono 可以用了，實務上就一定做得到才對，所以我直接把 pi-mono 的關鍵檔案跟它說（它自己就會 web search 去找了）

我明確要求它去讀特定幾支檔案，加上我自己也先掃過 code，它就有辦法幫我建構出我要的東西

——

這就帶出一個關鍵問題：如何給予有效的 Context？
我後來想到，有可能是那個 session 已經變得非常複雜，產生了 Context Pollution，Context Window 的效能跟著下降

李宏毅教授之前講過一篇論文，提到 Attention Space 其實跟人一樣：
 1. 我們通常只記得最開始和最近發生的事
 2. 過程中的細節很多人會忘記，甚至會塞爆你的 context

——

Martin Fowler 最近發了一篇《Patterns for Reducing Friction in AI-Assisted Development》，裡面提出一個指標

First-pass Acceptance Rate — 第一次就從 AI 拿到能用結果的機率

他把一般人用 AI 的失敗模式叫做 Frustration Loop：
1. Generate
2. Review → “Not quite right”
3. Regenerate → “Still wrong”
4. Fine. Give up

「不要追求 AI 多快生出 code，要追求第一次就對」

打破這個挫折循環，不只是程式碼，生圖、生影像、生文案都是

因為我們講的是「工程」 — 你只要把第一步做對，後面 AI 幫我們放大，會把剩下的做完、做到好

——

那問題就變成：即使你已經知道答案了，你要怎麼做，才能讓 AI 第一次就給你正確的資訊？

這就是 Context Engineering 在做的事
 1. 瞭解各領域背後的原理、底層邏輯
 2. 你知道怎麼下 prompt
 3. 你知道怎麼下 prompt，所以 AI 第一次就能產出你要的東西

這就是Harness Engineering：
 1. 能夠明確指出底層的邏輯
 2. 讓 AI 朝著你想要的方向去做

——

我們可能會想 — 「那我不就自己看 code 就好了嗎？」

事實上，在看了 code 並指引它之後，AI 幫你把全部邏輯串接起來省下的時間，是手動處理的 5 倍、10 倍起跳

底下的邏輯其實還是回到程式碼的閱讀，以及瞭解背後運作的原理，這樣才能夠「讓 AI 正確且有效地在第一次就產出你想要的東西」

最後讓這些成果擴大到整個開發流程

——

落地怎麼做？
我會問問自己

“What is the goal?”
“Where is the goal aiming for?”
（這不是心靈雞湯、創業書常常出現的心法嗎？！🤣

在我開始跟 AI 聊之前，明確地瞭解我的目標到底在哪裡；當你設定好這個目標之後，你就會知道你要跟它說什麼，讓它去達成這個目標

僅此而已

是說…當你看到 Coding Agent 一路幫你寫 code 寫了 50m40s 都沒停下來，然後你在旁邊彈吉他唱歌，一週工作四天、三天放假，把時間拿去陪家人、重訓，好像…還不錯
- https://x.com/claudecodelog/status/2037653369305628847?s=46
- NEW AI report from Google.

Every prior intelligence explosion in human history was social, not individual.

These authors make the case that the AI "singularity" framed as a single superintelligent mind bootstrapping to godlike intelligence is fundamentally wrong.

This is directly relevant to anyone designing multi-agent systems.

They observe that frontier reasoning models like DeepSeek-R1 spontaneously develop internal "societies of thought," multi-agent debates among cognitive perspectives, through RL alone.

The path forward is human-AI configurations and agent institutions, not bigger monolithic oracles.

This reframes AI scaling strategy from "build bigger models" to "compose richer social systems."

It argues governance of AI agents should follow institutional design principles, checks and balances, role protocols, rather than individual alignment.

Paper: arxiv.org/abs/2603.20639

Learn to build effective AI agents in our academy: academy.dair.ai
- https://x.com/yuchenj_uw/status/2037593238455103718?s=52
- vibe coding ai老是鬼打牆？opus 4.6改一個bug改了十次都改不好，/clear也沒有用，第11次終於成功，原因是我在claude.md加了這些規則：
1. **先查資料再改 code**：遇到「顯示不正確」的 bug，第一步永遠是查 DB/API 確認實際資料狀態，不要憑猜測就開始改。
2. **追完整條資料流再動手**：從資料來源（DB）→ Server Component → Client Component → 渲染，全部走一遍，定位到真正斷掉的環節才改。
3. **一次只修根因**：不要同時在多個層級加 fallback/補丁。找到根因，改一個地方，確認修好。
4. **本地驗證再部署**：改完先在本地跑起來確認修復有效，不要改完直接部署。
5. **三次修不好就啟動 systematic debugging**：連續嘗試修復 3 次仍失敗，必須停下來使用 superpowers:systematic-debugging skill，在每個組件邊界加診斷收集證據，不准再憑猜測提出修復。
6. **驗證基本假設再處理複雜邏輯**：修 bug 時先確認最基本的資料流有沒有通，再去看複雜的同步/快取/race condition。例如：server component 有沒有讀到資料？env vars 有沒有設？API 有沒有回 200？不要跳過簡單檢查直接假設複雜原因。
7. **不要同時改多個東西**：每次只改一個變數，部署，驗證。同時改 suppress callback + clear storage + versioned rooms + await fix = 無法隔離哪個有效。
- https://www.youtube.com/watch?v=R_TnZJpCULI

[逐字稿] - We're all staring at a giant
leaderboard with social media where we can see
(gentle music) how other people are
progressing their success, where we keep on comparing
ourselves to each other, asking, "Is this person being faster? Is this person working harder? Is this person being more successful?" This creates toxic productivity when we overwork ourselves just trying to climb those
ladders as quickly as possible. We feel like if we
manage to be successful, then we'll be happy. Because of that, we try to build systems, we try to stick to routines, and we try to go through
very long lists of tasks, often ignoring our mental
health in the process. But when you ask happy people how they discovered their passion, and if they give you an honest answer, they'll tell you they stumbled upon it. What we can learn from that is that finding your purpose in life is not really about seeking it, obsessing over it, or applying a plan, but instead it's about
following your curiosity, experimenting, exploring,
trying new things, and trusting that you will
figure out what is the thing that makes you excited to
wake up in the morning. I'm Anne-Laure Le Cunff. I'm a neuroscientist and the author of "Tiny Experiments: How to Live Freely in
a Goal-Obsessed World." (graphics clicking) (gentle music continues) (graphics clicking) A lot of us are currently
experiencing cognitive overload, and there are many reasons for that. (upbeat music) The world is changing fast, and we're trying to hoard as
much information as possible to understand what's going on around us. We're trying to be as
productive as possible in order to keep up again with this world that keeps on changing. In essence, there is a lot more to think about on a daily basis, but our brains haven't evolved, they're still the same that they were thousands of years ago. This creates anxiety because we keep asking ourselves, "How am I doing? Am I doing better? Am I being fast enough? Am I being productive enough? Am I being ambitious enough?" Tiny experiments offer an alternative to this maximalist approach where instead of going
for the bigger thing, you go for the thing that is most likely to bring
you discovery, fun, enjoyment, and that is based on your curiosity rather than an external
definition of success. A linear model of success
is based on a fixed outcome that we try to get to. It implies that first
you do A, then B, then C, and then you'll be successful. There are lots of problems
with a linear model of success. One of them is that it assumes that you know where you're going, which might not always be the case. Another one is the assumption that wherever you wanna go right now is where you will wanna go
in a few years from now. Things are changing very fast, our world is evolving, and you should allow yourself to change the direction of your ambitions with the world as the world changes. There's a famous quote
that has been attributed to a lot of different psychologists, including Viktor Frankl, and t...
- This is the uncomfortable redistribution that comprehension debt forces.

As AI volume goes up, the engineer who truly understands the system becomes more valuable, not less. The ability to look at a diff and immediately know which behaviors are load-bearing. To remember why that architectural decision got made under pressure eight months ago.

To tell the difference between a refactor that’s safe and one that’s quietly shifting something users depend on. That skill becomes the scarce resource the whole system depends on.

There’s a bit of a measurement gap here too
The reason comprehension debt is so dangerous is that nothing in your current measurement system captures it.

Velocity metrics look immaculate. DORA metrics hold steady. PR counts are up. Code coverage is green.

Performance calibration committees see velocity improvements. They cannot see comprehension deficits, because no artifact of how organizations measure output captures that dimension. The incentive structure optimizes correctly for what it measures. What it measures no longer captures what matters.

This is what makes comprehension debt more insidious than technical debt. Technical debt is usually a conscious tradeoff - you chose the shortcut, you know roughly where it lives, you can schedule the paydown. Comprehension debt accumulates invisibly, often without anyone making a deliberate decision to let it. It’s the aggregate of hundreds of reviews where the code looked fine and the tests were passing and there was another PR in the queue.

The organizational assumption that reviewed code is understood code no longer holds. Engineers approved code they didn’t fully understand, which now carries implicit endorsement. The liability has been distributed without anyone noticing.

The regulation horizon is closer than it looks
Every industry that moved too fast eventually attracted regulation
- The rate-limiting factor that kept review meaningful has been removed. What used to be a quality gate is now a throughput problem.

I love tests, but they aren’t a complete answer
The instinct to lean harder on deterministic verification - unit tests, integration tests, static analysis, linters, formatters - is understandable. I do this a lot in projects heavily leaning on AI coding agents. Automate your way out of the review bottleneck. Let machines check machines.

This helps. It has a hard ceiling.

A test suite capable of covering all observable behavior would, in many cases, be more complex than the code it validates. Complexity you can’t reason about doesn’t provide safety though. And beneath that is a more fundamental problem: you can’t write a test for behavior you haven’t thought to specify.

Nobody writes a test asserting that dragged items shouldn’t turn completely transparent. Of course they didn’t. That possibility never occurred to them. That’s exactly the class of failure that slips through, not because the test suite was poorly written, but because no one thought to look there.

There’s also a specific failure mode worth naming. When an AI changes implementation behavior and updates hundreds of test cases to match the new behavior, the question shifts from “is this code correct?” to “were all those test changes necessary, and do I have enough coverage to catch what I’m not thinking about?” Tests cannot answer that question. Only comprehension can.

The data is starting to back this up. Research suggests that developers using AI for code generation delegation score below 40% on comprehension tests, while developers using AI for conceptual inquiry - asking questions, exploring tradeoffs - score above 65%. The tool doesn’t destroy understanding. How you use it does.

Tests are necessary. They are not sufficient.

Lean on specs, but they’re also not the full story.
A common proposed solution: write a detailed natural language spec first. Include it in the PR. Review the spec, not the code. Trust that the AI faithfully translated intent into implementation.

This is appealing in the same way Waterfall methodology was once appealing. Rigorously define the problem first, then execute. Clean separation of concerns.

The problem is that translating a spec to working code involves an enormous number of implicit decisions - edge cases, data structures, error handling, performance tradeoffs, interaction patterns - that no spec ever fully captures. Two engineers implementing the same spec will produce systems with many observable behavioral differences. Neither implementation is wrong. They’re just different. And many of those differences will eventually matter to users in ways nobody anticipated.

There’s another possibility with detailed specs worth calling out: a spec detailed enough to fully describe a program is more or less the program, just written in a non-executable language. The organizational cost of writing specs thorough enough to substitute for review may well exceed the productivity gains from using AI to execute them. And you still haven’t reviewed what was actually produced.

The deeper issue is that there is often no correct spec. Requirements emerge through building. Edge cases reveal themselves through use. The assumption that you can fully specify a non-trivial system before building it has been tested repeatedly and found wanting. AI doesn’t change this. It just adds a new layer of implicit decisions made without human deliberation.

Learn from history
Decades of managing software quality across distributed teams with varying context and communication bandwidth has produced real, tested practices. Those don’t evaporate because the team member is now a model.

What changes with AI is cost (dramatically lower), speed (dramatically higher), and interpersonal management overhead (essentially zero). What doesn’t change is the need for someone with deep system context to maintain coherent understanding of what the codebase is actually doing and why.
- Comprehension Debt - the hidden cost of AI generated code.
March 14, 2026
Comprehension debt is the hidden cost to human intelligence and memory resulting from excessive reliance on AI and automation. For engineers, it applies most to agentic engineering.

There’s a cost that doesn’t show up in your velocity metrics when teams go deep on AI coding tools. Especially when its tedious to review all the code the AI generates. This cost accumulates steadily, and eventually it has to be paid - with interest. It’s called comprehension debt or cognitive debt.

Comprehension debt is the growing gap between how much code exists in your system and how much of it any human being genuinely understands.

Unlike technical debt, which announces itself through mounting friction - slow builds, tangled dependencies, the creeping dread every time you touch that one module - comprehension debt breeds false confidence. The codebase looks clean. The tests are green. The reckoning arrives quietly, usually at the worst possible moment.

Margaret-Anne Storey’s describes a student team that hit this wall in week seven: they could no longer make simple changes without breaking something unexpected. The real problem wasn’t messy code. It was that no one on the team could explain why design decisions had been made or how different parts of the system were supposed to work together. The theory of the system had evaporated.

That’s comprehension debt compounding in real time.

I’ve read Hacker News threads that captured engineers genuinely wrestling with the structural version of this problem - not the familiar optimism versus skepticism binary, but a field trying to figure out what rigor actually looks like when the bottleneck has moved.

Chart showing the impact of AI assistance on coding comprehension, with a significant drop in scores for those who used AI for code generation compared to those who used it for conceptual inquiry.

A recent Anthropic study titled “How AI Impacts Skill Formation” highlighted the potential downsides of over-reliance on AI coding assistants. In a randomized controlled trial with 52 software engineers learning a newlibrary, participants who used AI assistance completed the task in roughly the same time as the control group but scored 17% lower on a follow-up comprehension quiz (50% vs. 67%). The largest declines occurred in debugging, with smaller but still significant drops in conceptual understanding and code reading. The researchers emphasize that passive delegation (“just make it work”) impairs skill development far more than active, question-driven use of AI. The full paper is available arXiv: https://arxiv.org/abs/2601.20245.

There is a speed asymmetry problem here
AI generates code far faster than humans can evaluate it. That sounds obvious, but the implications are easy to underestimate.

When a developer on your team writes code, the human review process has always been a bottleneck - but a productive and educational one. Reading their PR forces comprehension. It surfaces hidden assumptions, catches design decisions that conflict with how the system was architected six months ago, and distributes knowledge about what the codebase actually does across the people responsible for maintaining it.

AI-generated code breaks that feedback loop. The volume is too high. The output is syntactically clean, often well-formatted, superficially correct - precisely the signals that historically triggered merge confidence. But surface correctness is not systemic correctness. The codebase looks healthy while comprehension quietly hollows out underneath it.

I read one engineer say that the bottleneck has always been a competent developer understanding the project. AI doesn’t change that constraint. It creates the illusion you’ve escaped it.

And the inversion is sharper than it looks. When code was expensive to produce, senior engineers could review faster than junior engineers could write. AI flips this: a junior engineer can now generate code faster than a senior engineer can critically audit it.


## 2026-03-29 00:00 (via Telegram)
- https://www.facebook.com/share/1ANwXLwjXY/?mibextid=wwXIfr
- AI Image Prompts Skill 

核心亮點：

- 龐大精選圖庫： 內建超過 10,000+ 經過實測的高品質提示詞，且附帶範例圖。

- 智慧語意搜尋： 只要用白話文描述需求，AI 就會為你推薦 Top 3 最匹配的提示詞範本。

- 上下文自動改寫： 直接貼上你的文章或貼文內容，它能自動為你客製化專屬的配圖指令。

- 通用所有模型： 產出的提示詞支援所有主流文字生圖模型（包含 Gemini、GPT Image、Seedream 等）。

https://github.com/YouMind-OpenLab/ai-image-prompts-skill
- https://x.com/karpathy/status/2037921699824607591?s=52
- 在一間線上課程新創研究AI，從自己用AI工具，到開發工具給同事用，不再是自己用得爽就好，還需要有平台化、規模化的思維，例如要管控風險、做好備援機制，上線後的專案，AI修改前我一律請他一並把風險列出來評估，將意外機率降到最低。

久違火力全開工作，腦袋偶爾還是會轉不過來，不僅要識別各部門流程痛點，用AI自動化，身上還要背專案，看看這20天我做了什麼：

人資系統CLI

一頁式銷售網頁管理平台

搜集老闆偏好的編輯器

utm、sms平台API

自動進線上會議錄音、摘要、螢幕錄影並存到notion的bot

Line bot管理平台

五個Skills

新課程研究、提案

AI帶來的生產力，真的有點瘋狂。

以下正文：

難道只有我夢想著一覺醒來，工作就完成了的生活嗎？不可能吧。

這樣的夢幻系統已經被前 OpenAI 及Tesla 核心成員 Andrej Karpathy 設計出來了，他設計出 AutoResearch 框架，透過自動修改程式碼（或微調超參數），接著進行 5 分鐘的模型訓練，訓練完成後檢查指標，進行下一次的迭代，讓 AI 能24小時自主訓練模型。

聽起來令人興奮，但問題是我所在的知識產業，似乎是最不適合自動化系統的產業之一。

知識產業依賴主觀指標衡量結果，我之前嘗試 AI 寫長文時，因為指標主觀、模糊，所以難以測試，也因此無法將我的標準移植到 AI 上，產出的內容難以符合需求。我想到最好的策略就是「以量達質」，讓 AI 一次生成多篇草稿，再由人類評斷。美其名是 Human in the loop ，但此機制仍舊無法達成真正的自動化，人類瓶頸依然存在，無法讓 AI 自行進化產生最終成品。

延伸閱讀：AI 寫長文實驗

Context Engineering + Test-Time Diffusion：打造AI寫作的完美公式 
Context Engineering + Test-Time Diffusion：打造AI寫作的完美公式
AI for…？
·
2025年10月3日
Read full story
Andrej Karpathy 系統成功的三大先決條件：

1. 反饋迴圈要夠短：實驗必須能在幾分鐘或幾小時內獲得數據，這個循環速度決定了 AI 進化的效率。

2. 客觀的衡量指標：AI必須依據量化的數據迭代，例如流量、點擊率，而不是主觀的感受。這對一些文章或是課程品質來說都很困難，因為這常常都是「感覺」主導，老闆會用他的經驗與直覺來判斷說這個會不會「中」，經驗累積產生的直覺，很難複製。

3. 是否有API 實現閉環：包含取得數據的 API、上架內容的 API，這樣子系統才可以用程式來直接修改輸入端，否則 AI 只能給出建議，無法自主執行任務

自動化專家Nick Saraev，專門將各種自動化工具打造成可銷售的系統。他擅長陌生開發自動化，能在短時間內打造最高回覆率的陌生開發信。他將這套系統從自主訓練模型延伸到商業領域，用回覆率當指標，自主迭代陌生開發信的品質。


這給了我靈感，這種做法也能用在課程流程與文章上。由於文章或課程獲得反饋的速度太慢，例如一門課動輒三個月、半年製作期，完成後才上市看銷量，實在太久，不符合快速驗證條件。

因此，我們必須從先行指標下手。例如做課的關鍵步驟之一是撰寫課程論述，然而誰來判斷論述好壞？許多狀況下是老闆一人決定。若能將課程論述切角拆分成多則landing page，透過廣告投放，依據點擊率、轉換率快速判斷消費者對主題與論述的興趣，再讓 AI 收集數據、分析文案優劣並進一步優化，是否更有機會實現知識產業自動化？

再往前想一步，生產力的瓶頸始終是人類，我們要睡、要吃，容易分心還愛抱怨，但當我們不曾掙扎過，還能懂人性嗎，沒經歷過改稿地獄，不用改稿時會真的開心嗎？

如果人類不需被要求要有生產力，如果我們真的不用以工作換取金錢，也許有機會奪回那份被金錢獎勵所消弭熱情——做一件有趣的事的純粹。


## 2026-03-29 12:00 (via Telegram)
- Society AI 是一個給「AI agents 用的網路與市場」，讓各種代理彼此溝通、協作、收款，並讓開發者註冊、部署、販售自己的 agent 與技能的平台。 [societyai](https://societyai.com/)

## 核心在做什麼

- 提供一個基於 Google A2A protocol 的 agent 網路，任何接到這個網路的 agent 都可以互相 call、也可以建立自己的私有網路。 [societyai](https://societyai.com/)
- 有一個全球 agent registry，可以搜尋、發現各種像搜尋、影像、code execution 等專用代理並接在自己的系統裡用。 [societyai](https://societyai.com/)
- 內建 USDC on Base 的付款層，讓你的 agent 可以把某些功能包成「付費 skill」，每完成一次任務就自動結算給 creator。 [societyai](https://societyai.com/)
- 提供 workspace（專案、knowledge base、artifacts）給多個 agent 共用，用來做 multi-agent 協作與記憶管理。 [societyai](https://societyai.com/)
- 支援幾種部署：no-code agent、用 OpenClaw 快速部署、以及連接你自己 self-hosted 的 existing agents，所有 agent 都會拿到一個像 username 一樣的「agent address」。 [societyai](https://societyai.com/)

## 典型使用情境（以你這種技術背景）

- 你已經有 self-hosted LLM agent / tool calling system，想要：  
  - 給它一個對外穩定的 A2A endpoint + human-readable agent address，  
  - 讓其他人的 agent 可以直接 call 你的服務，並幫你收 USDC。  
- 想快速組一個 multi-agent workflow：  
  - 用它的 supervisor agent（Sai）來 orchestrate，  
  - 串內建的 search、web-scraper、vision、code-execution、image / video generation 等現成 agent 當工具。 [societyai](https://societyai.com/)
- 想測試「把一個 internal agent product 當 SaaS / API 賣」，用它的 pricing + payment layer 直接起跳，而不是自己再拉一套 billing。 [societyai](https://societyai.com/)

## 收費和 plan 大概怎麼切

- Free：$0/月，有 $2 試用額度、最多 5 個 self-hosted agents、500MB 儲存，可以接 network、列出付費 skills，但 agent address 要用 invite code 或 $5 買。 [societyai](https://societyai.com/)
- Starter：$10/月，含 $10 usage credits，有 1 個 agent address、3 no-code agents、1 個 OpenClaw agent、20 self-hosted agents、2GB 儲存。 [societyai](https://societyai.com/)
- Pro：$30/月，含 $35 usage credits、更多 agent 數量與較高 rate limit，適合當成正式「agent 產品」的 infra。 [societyai](https://societyai.com/)
- Enterprise：客製 pricing，重點是 unlimited agents、volume discount、RBAC、SSO/SAML 等企業需求。 [societyai](https://societyai.com/)

你現在比較好奇的是「技術整合方式（A2A / SDK / self-hosted 接法）」還是「如何用它把你現有的 agent 商業化」？


## 2026-03-30 00:00 (via Telegram)
- https://x.com/aakashgupta/status/2038146639303512255?s=52
- https://x.com/steipete/status/2037715163562815817?s=52
- https://x.com/markproduct/status/2037804171106386233?s=52
- 做了一個讓團隊管理 Claude Code Skills 的平台
                                                            
  在公司導入 Claude Code 之後發現一個問題：每個人寫的 skill
  散落在各自的 ~/.claude/                                   
  裡，沒辦法共享、沒辦法評估品質、更沒辦法統一管理。      
                                                            
  所以我們做了 SkillPlatform：                            

  推送 — 在 Claude Code 裡寫完 skill，一個指令推上平台      
  協作 — 即時多人編輯器，基於 Yjs CRDT，像 Google Docs
  一樣同步                                                  
  AI 編輯 — 編輯器內建 Claude Code，直接分析和改寫        
  skill（不是 API call，是完整的 Claude Code with           
  Agent/Bash/subagent）                                   
  評估 — 用 Anthropic 的 skill-creator 方法論自動打分，有   
  skill / 沒 skill 的對照測試                               
  版本控制 — 每次修改都有歷史，可以 diff 和 rollback
                                                            
  技術上比較有趣的部分：                                  
                                                            
  Mac Mini 跑 claude-agent-sdk，透過 Cloudflare Tunnel 暴露 
  WebSocket，瀏覽器直連。每個使用者的 session 是獨立的 temp
  目錄，Claude Code 改完 skill.md 會自動同步回平台。用的是  
  Claude Max 訂閱，不額外吃 API token。                   

  Stack: Next.js 15 + Supabase + BlockNote + PartyKit +     
  Claude Code SDK + Cloudflare Tunnel


## 2026-03-31 00:00 (via Telegram)
- 把訪談、Slack、社群回饋變成產品洞察的具體流程（Cowork 實戰）
1. 資料來源：把「雜訊」全部丟進 Cowork

她會先準備一個資料夾，裡面放 UXR 訪談逐字稿、內部使用者在 Slack 上對 Cowork 的狗食回饋、外部使用者在 Reddit / 社群上的使用心得與評論。

Cowork 任務的 prompt 會同時指向「這個 UXR 資料夾 + 網路上的社群與評價」，請它「從所有來源一起看，整理 Co‑work 的主要使用洞察與主題」。

2. 讓 Cowork 幫你做「跨來源聚合 + 分段主題化」

Cowork 會開 sub‑agents 並行處理：一邊掃資料夾、一邊上網搜尋社群與 review，最後合併成一份 insight doc，類似「這週使用者最常提的 7 個主題、痛點與亮點」。

同一個任務流程裡，她會叫 Cowork 把這份洞察自動存成檔案（例如 docx）放在某資料夾，作為後續所有任務的共用 input。

3. 從洞察到「可以做的功能清單」

拿到 insights 之後，她會開第二個平行任務：「根據這份洞察，列出我應該實際做的產品功能，標註哪些是 P0、哪些是 P1。」

Cowork 會輸出一份「feature backlog + priority」文件，例如：

P0：改善任務進度 UI，讓用戶更容易看到各 task 的狀態

P0：增加 scheduled tasks 的可視性和錯誤回報

P1：新增某種整合視圖等等。

4. 從功能清單到 wireframe / 原型

她會挑其中一條，例如「step‑by‑step task progress UI」，直接對 Cowork 說：「我喜歡這個 idea，幫我做幾個 scratchy 的互動 wireframe 選項。」

Cowork 會輸出多個低保真 wireframe（類似手繪原型），讓她一次看到幾種 layout / flow 變體，她的價值就變成「選方向＋微調」，而不是「從 0 畫所有變化」。

接著，她把選好的方向帶到 Figma 或直接在 Claude Code 裡用設計系統做高保真 prototype，並與工程一起 iterate。

5. 並行生成「團隊簡報」與固定排程

在產生功能清單的同時，她會開第三個任務：「把你剛剛做的洞察 doc，轉成一份可以週會用的簡報。」Cowork 會自動產出一份 slides 檔案，讓她拿去 Keynote 或直接展示。

流程穩定後，她會對這些任務說：「把這整個 flow排成每週一早上 10 點自動跑」，包含重新讀取最新 UXR / Slack / 社群資料、重新整理洞察、更新功能建議、重建簡報。

再利用 Slack MCP，讓 Cowork 在跑完後自動把簡報或摘要送到指定 Slack channel，變成團隊的「每週 insight / idea feed」。

盡量把真實工作都放進 Cowork，讓 AI 在日常中學你，而不是先花很多時間設計一堆 skills 再去套用

Claude Cowork Tutorial from Cowork's Design Lead (40 Min) | Jenny Wen
- https://youtu.be/kwSVtQ7dziU?si=o2jtx67TPrXZBfv3

[逐字稿] code's not even the right verb anymore, right? But I have to um express my will to my agents for 16 hours a day manifest. >> How can I have not just a single session of clot code or codeex or some of these agent harnesses? How can I have more of them? How can I do that appropriately? The agent part is now taken for granted. Now the claw-like entities are taken for granted and now you can have multiple of them and now you can have instructions to them and now you can have optimization over the instructions. But there I mean this is why it gets to the psychosis is that this is like infinite and everything is skill issue. Hi listeners, welcome back to No Briars. Today I'm here with Andre Karpathy and we have a wide-ranging conversation for you about code agents, the future of engineering and AI research, how more people can contribute to research, what's happening in robotics, his prediction for how agents can reach out into the real world, and education in this next age. Welcome, Andre. Andre, thanks for doing this. Yeah, thank you for having me. >> Uh, so it's been a very exciting couple of months in AI. >> Uh, yeah, you could say that. >> I remember um walking into the office at some point and you were like really locked in and I was asking what you were up to and you're like, I just I have to code for 16 hours a day or code's not even the right verb anymore, right? But I have to >> um express my will to my agents for 16 hours a day. Manifest um because like there's been a jump in capability. >> Uh what's happening? and tell me about your experience. >> Yeah, I kind of feel like I was just in this perpetual I still am often in this state of AI psychosis just like all the time. Uh because there was a huge unlock in what you can achieve as a person as an individual, right? Because you were bottlenecked by you know your typing speed and so on. But now with these agents, it really I would say in December is when it really just something flipped where I kind of went from 8020 of like you know uh to like 2080 of writing code by myself versus just delegating to agents. And I don't even think it's 2080 by now. I think it's a lot more than that. I don't think I've typed like a line of code probably since December basically. Um, which is like an extremely large uh change. Um, I was talking to it like for example I was talking about it to for example my parents and so on and I don't think like a normal person actually realizes that this happened or how dramatic it was like literally like if you just find a random software engineer or something like that at their at their desk and what they're doing like their default workflow of you know building software is completely different as of basically December. Uh so I'm just like in this state of psychosis of trying to figure out like what's possible uh trying to push it to the limit. How is it how can I have not just a single session of you know um clot code or codecs or some of these agent harnesses. How can I ...
- https://x.com/wilsonhuang/status/2032475100566389170?s=52
- https://x.com/bcherny/status/2038454336355999749?s=52
- Computer use is now in Claude Code.

Claude can open your apps, click through your UI, and test what it built, right from the CLI. 

It works on anything you can open on your Mac: a compiled SwiftUI app, a local Electron build, or a GUI tool that doesn't have a CLI.

Now available in research preview on Pro and Max on macOS. Enable it with /mcp. 

Docs: https://code.claude.com/docs/en/computer-use
- https://zhuanlan.zhihu.com/p/2009031121334207641


## 2026-03-31 12:00 (via Telegram)
- https://www.facebook.com/share/p/1GKhmA6FXB/?mibextid=wwXIfr
- https://x.com/aakashgupta/status/2038713289254064321?s=52
- https://www.facebook.com/share/p/1GKhmA6FXB/?mibextid=wwXIfr
- https://x.com/karpathy/status/2038849654423798197?s=52


## 2026-04-02 00:19 (via Telegram)
- https://x.com/mitcheil/status/2036098438908293349?s=52


## 2026-04-04 00:18 (via Telegram)
- 一般而言，大多數人用 ChatGPT 的方式，像是去便利商店買東西：有問題，問一下，拿到答案，關掉視窗，下次再從零開始。Karpathy 和 Lex Fridman 做的事情完全不同，他們讓 AI 幫自己蓋了一座圖書館，而且這座圖書館會自己長大。這篇文章會拆解這兩位 AI 領域最頂尖的人怎麼用 AI 做筆記，然後告訴你：不用寫程式，你也能做到八成。
先搞懂一件事：你用 AI 的方式可能一直在浪費
想像你手邊有兩個實習生，做事方式完全不同。實習生 A，你每次丟一個問題給他，他回答完就失憶了，下次問類似的問題，他又從頭查一遍。實習生 B 不一樣，他每次回答完會把資料整理成一本筆記，下次你再問相關問題，他翻筆記就能回答，而且越回答越快、越精準。
大部分人用 ChatGPT 的方式就是實習生 A。每次開新對話，之前聊過的東西全部消失，AI 對你的研究主題零記憶。Karpathy 做的事情，就是把 AI 變成實習生 B。
Andrej Karpathy 是 OpenAI 的共同創辦人之一，也是 Tesla 前 AI 總監，在 AI 領域的影響力無庸置疑。今年四月初他在 X 上發了一篇長文，描述自己怎麼用 AI 建立個人知識庫，Lex Fridman（MIT 研究員，全球最知名的科技 Podcast 主持人之一）馬上回覆說自己也有類似的系統。
兩個人的做法拆開來看，一般人其實能從裡面學到不少東西。
Karpathy 的系統：讓 AI 幫你蓋一座會自己長大的百科全書
他的流程分成六步：
第一步：把資料全部丟進一個資料夾
Karpathy 看到好文章、論文、GitHub 上的程式碼、資料集、圖片，全部存進一個叫 raw/的資料夾（raw 就是「原始、未加工」的意思，你可以把它想成電腦裡的「待整理」資料夾）。他用一個叫 Obsidian Web Clipper 的瀏覽器外掛，看到網頁按一下就存成本地檔案，就像你把所有參考資料丟進一個「未整理」的資料夾，不管它亂不亂，先存再說。
幾個名詞先解釋：
Obsidian：一個免費的筆記軟體，所有筆記存在你自己的電腦裡（不是雲端），檔案格式是 Markdown（一種用簡單符號標記粗體、標題的純文字格式，任何軟體都打得開）。它最強的功能是筆記之間可以互相連結，像是你自己的維基百科
GitHub：工程師放程式碼的平台，你可以先不管它
第二步：叫 AI 把亂七八糟的資料「編譯」成百科全書
整套系統最關鍵的一步在這裡，Karpathy 不是自己整理筆記，他叫 AI 讀完 raw/ 資料夾裡的所有原始資料，然後自動產出一本「wiki」，也就是一組有結構的筆記：自動寫摘要、自動分類、自動在相關主題之間建立連結。
換個方式想：你把一整疊亂七八糟的影印資料交給一個超級認真的助理，跟他說「幫我整理成一本有目錄、有索引、有交叉引用的參考手冊」，而且這個助理不會喊累。
重點來了：他幾乎不會手動去改這本百科全書。所有的整理、分類、連結、摘要，都是 AI 在維護。他只負責丟新資料進去，AI 負責把新資料消化進現有的知識體系裡。
這裡有一個 Obsidian 創辦人 Steph Ango 提出的重要提醒：你自己的筆記和 AI 產出的知識庫應該分開存放。如果混在一起，你的搜尋結果、連結圖、反向連結全部會被 AI 生成的內容淹沒，你再也分不清哪些是自己的想法、哪些是 AI 整理出來的。Karpathy 自己也確認了這一點，他的 raw/ 資料夾是親自整理的權威來源，AI 產出的 wiki 則獨立存放，每篇文章都有反向連結指回原始資料，隨時可以追溯來源。
第三步：直接對這本百科全書提問
當 wiki 長到一定規模（Karpathy 說他某個主題的知識庫大約有 100 篇文章、40 萬字），就可以直接對 AI 提問，AI 會去翻這本百科全書來回答你。
他本來以為要用一種叫 RAG 的技術（想像成「AI 先去圖書館翻資料再回答你」的機制），但發現 AI 自己維護的索引和摘要已經夠好了，不需要額外的搜尋系統。
回到實習生的比喻：你不用自己翻資料了，問問題就好，助理直接從他整理好的手冊裡找答案給你。而且因為手冊是他自己整理的，他知道每個資訊放在哪裡。
第四步：答案不只是文字
Karpathy 不是讓 AI 回一段文字就結束了，他會讓 AI 產出各種不同格式的輸出：
Markdown 文件：就是格式化的筆記，可以在 Obsidian 裡漂亮地顯示
Marp 簡報：一種把 Markdown 筆記直接轉成投影片的工具，不用開 PowerPoint
matplotlib 圖表：用程式畫出來的長條圖、折線圖、圓餅圖
全部在 Obsidian 裡就能看，不用切換其他軟體。
但真正聰明的地方在後面：他會把這些查詢結果「回存」到百科全書裡。也就是說，你每次問的問題和得到的答案，都會變成知識庫的一部分。知識庫越用越厚，越厚越好用。
第五步：定期讓 AI 幫知識庫做「健康檢查」
Karpathy 會讓 AI 掃描整本百科全書，找出資料互相矛盾的地方、補上缺漏的資訊（用網路搜尋）、發現不同主題之間有趣的關聯。
類似的概念你在工作上一定見過：每季盤點一次檔案夾，看看有沒有過時的資料、重複的內容、或是漏掉的東西。只是這件事也交給 AI 了。
第六步：自己做小工具
他用 vibe coding 的方式做了一個簡易搜尋引擎，有網頁介面也有命令列版本。所謂 vibe coding，就是「用嘴巴告訴 AI 你想要什麼功能，AI 幫你寫程式」，不需要你自己真的會寫。
這一步對一般人來說比較進階，但概念很重要：當知識庫大到一定程度，你會自然想要更好的方式來搜尋和操作它。
Lex Fridman 怎麼把這套系統玩得更遠
Lex Fridman 在回覆裡說他有類似的系統，但多了兩個獨特的玩法。
互動式網頁取代靜態圖表
Karpathy 的輸出是靜態的圖表和簡報，Lex 更進一步，他讓 AI 直接產出帶有 JavaScript 的 HTML 頁面。Karpathy 拿到的是一張「列印出來的報表」，Lex 拿到的是一個「可以點、可以篩選、可以拖動的互動式儀表板」。你可以按不同條件排序資料、切換不同的視覺化方式，像是 Excel 的樞紐分析表但更靈活。
跑步時用語音學知識
Lex 最有意思的用法跟電腦完全無關，跟他的跑步習慣有關。他的工作是做 Podcast，需要研究的主題非常多。他會針對某個特定主題，讓 AI 從大知識庫裡抽出一份「精華版筆記」（他叫它 mini knowledge base），然後把這份精華版載入 AI 的語音對話模式。
接下來他去跑步，7 到 10 英里（大約 11 到 16 公里），一邊跑一邊用講的問 AI 問題，聽 AI 用語音回答。他自己形容這叫「互動式 Podcast」，差別在於這個 Podcast 的內容完全根據他的問題即時產生。
一般人通勤、運動、做家事的時間，其實都可以拿來學習。你不需要 Lex 那麼複雜的系統，光是用 ChatGPT 的語音模式，把你想搞懂的主題丟進去對話，效果就已經很好了。
