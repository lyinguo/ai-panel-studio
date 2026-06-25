/** Mock 数据 —— 模拟 "AGI 是否应该暂停研发" 圆桌讨论 */

export const PARTICIPANTS = [
  {
    id: 1,
    role: "host",
    name: "陈思远",
    title: "AI 伦理与治理专家",
    stance: "保持中立，引导讨论聚焦核心议题，确保各方观点得到充分表达。",
    color_code: "#4A90D9",
    order: 0,
  },
  {
    id: 2,
    role: "expert",
    name: "李薇",
    title: "资深机器学习研究员",
    stance: "技术本身是中立的，关键在于应用场景和监管框架的完善。",
    color_code: "#FF6B6B",
    order: 1,
  },
  {
    id: 3,
    role: "expert",
    name: "王磊",
    title: "人工智能安全专家",
    stance: "主张在 AGI 研发上采取审慎渐进策略，安全护栏必须前置。",
    color_code: "#50C878",
    order: 2,
  },
  {
    id: 4,
    role: "expert",
    name: "赵雨桐",
    title: "计算神经科学博士",
    stance: "从认知科学角度论证，当前 AI 距离真正理解还有本质差距。",
    color_code: "#FFD700",
    order: 3,
  },
  {
    id: 5,
    role: "expert",
    name: "孙明达",
    title: "开源 AI 社区发起人",
    stance: "强调开放研究对 AI 安全的重要性，透明度和可复现性是底线。",
    color_code: "#9B59B6",
    order: 4,
  },
];

/** 模拟 SSE 事件序列（按时间顺序播放） */
export const MOCK_EVENTS = [
  // 主持人开场
  {
    type: "guest_status_change",
    data: { participant_id: 1, status: "speaking", timestamp: "T+0s" },
    delay: 500,
  },
  {
    type: "message_chunk",
    data: {
      participant_id: 1,
      content:
        "各位专家好，欢迎参加今天的圆桌讨论。我们今天的话题是：AGI 是否应该暂停研发？这是一个关乎人类未来的重要议题。在座各位来自不同领域，相信能带来多元视角。让我们先从李薇研究员开始，您如何看待这个问题？",
      is_final: true,
    },
    delay: 3000,
  },
  {
    type: "guest_status_change",
    data: { participant_id: 1, status: "idle", timestamp: "T+3s" },
    delay: 200,
  },
  // 专家 A 发言
  {
    type: "guest_status_change",
    data: { participant_id: 2, status: "thinking", timestamp: "T+3.5s" },
    delay: 400,
  },
  {
    type: "guest_status_change",
    data: { participant_id: 2, status: "speaking", timestamp: "T+5s" },
    delay: 1200,
  },
  {
    type: "message_chunk",
    data: {
      participant_id: 2,
      content:
        "谢谢主持人。我的观点是，AGI 研发不应暂停。技术发展有其内在规律，暂停不仅难以执行，还可能让相关研究转入地下，反而更危险。关键是要建立同步的伦理审查机制。",
      is_final: true,
    },
    delay: 3500,
  },
  {
    type: "guest_status_change",
    data: { participant_id: 2, status: "idle", timestamp: "T+8.5s" },
    delay: 200,
  },
  // 专家 B 抢话
  {
    type: "guest_status_change",
    data: { participant_id: 3, status: "speaking", timestamp: "T+9s" },
    delay: 800,
  },
  {
    type: "message_chunk",
    data: {
      participant_id: 3,
      content:
        "我不同意暂停论，但我也不同意李研究员的无限制发展论。我主张的是审慎渐进。在没有完全理解 AGI 的安全边界之前，大规模部署是极其危险的。我们需要像核能一样，先建好安全壳再启动反应堆。",
      is_final: true,
    },
    delay: 4000,
  },
  {
    type: "guest_status_change",
    data: { participant_id: 3, status: "idle", timestamp: "T+13s" },
    delay: 200,
  },
  // 第一次共识更新
  {
    type: "consensus_update",
    data: {
      agreements: ["AGI 发展需要建立完善的安全框架", "伦理审查机制不可或缺"],
      divergences: ["是否应该暂停研发的时间表分歧", "发展与安全的优先级之争"],
    },
    delay: 1000,
  },
  // 专家 C 发言
  {
    type: "guest_status_change",
    data: { participant_id: 4, status: "speaking", timestamp: "T+15s" },
    delay: 800,
  },
  {
    type: "message_chunk",
    data: {
      participant_id: 4,
      content:
        "我从认知科学的角度补充一点。当前的深度学习系统本质上是在做模式匹配，距离真正的理解还有本质差距。我认为讨论 AGI 暂停为时过早，我们连强人工智能的门槛都还没摸到。",
      is_final: true,
    },
    delay: 4000,
  },
  {
    type: "guest_status_change",
    data: { participant_id: 4, status: "idle", timestamp: "T+19s" },
    delay: 200,
  },
  // 专家 D 反驳
  {
    type: "guest_status_change",
    data: { participant_id: 5, status: "speaking", timestamp: "T+20s" },
    delay: 800,
  },
  {
    type: "message_chunk",
    data: {
      participant_id: 5,
      content:
        "赵博士的观点我部分认同，但我想强调另一个维度。无论 AGI 是否临近，开源社区的研究透明度才是最核心的安全保障。闭门造车才是最大的风险。我们应该推动更多开源研究，让全世界的智慧共同参与安全设计。",
      is_final: true,
    },
    delay: 4000,
  },
  {
    type: "guest_status_change",
    data: { participant_id: 5, status: "idle", timestamp: "T+24s" },
    delay: 200,
  },
  // 第二次共识更新
  {
    type: "consensus_update",
    data: {
      agreements: [
        "AGI 发展需要建立全球监管框架",
        "研究透明度是安全发展的前提",
        "伦理审查机制必须前置",
      ],
      divergences: [
        "暂停研发 vs 渐进式推进的时间表分歧",
        "开源 vs 闭源的治理路径分歧",
        "AGI 实现时间表的认知差异",
      ],
    },
    delay: 1200,
  },
  // 主持人总结
  {
    type: "guest_status_change",
    data: { participant_id: 1, status: "speaking", timestamp: "T+26s" },
    delay: 600,
  },
  {
    type: "message_chunk",
    data: {
      participant_id: 1,
      content:
        "感谢各位专家的精彩发言。今天我们看到了不同角度的深刻洞见：从技术发展的不可阻挡性，到安全优先的审慎态度，再到认知科学的基础反思，以及开源透明的治理主张。虽然我们在时间表和路径上存在分歧，但在安全框架和伦理审查的必要性上达成了基本共识。讨论到此结束，感谢各位。",
      is_final: true,
    },
    delay: 5000,
  },
  {
    type: "guest_status_change",
    data: { participant_id: 1, status: "idle", timestamp: "T+31s" },
    delay: 200,
  },
  // 最终共识
  {
    type: "consensus_update",
    data: {
      agreements: [
        "AGI 发展需要建立全球监管框架",
        "研究透明度是安全发展的前提",
        "伦理审查机制必须前置",
        "多方参与比单一主体更安全",
      ],
      divergences: [
        "暂停研发 vs 渐进式推进的时间表分歧",
        "开源 vs 闭源的治理路径分歧",
        "AGI 实现时间表的认知差异",
      ],
    },
    delay: 800,
  },
];