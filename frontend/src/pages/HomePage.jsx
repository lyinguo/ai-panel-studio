import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const API = "http://localhost:8000";

function HomePage() {
  const [discussions, setDiscussions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [topic, setTopic] = useState("");
  const [expertCount, setExpertCount] = useState(4);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    fetchDiscussions();
  }, []);

  const fetchDiscussions = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API}/api/discussions`);
      if (resp.ok) {
        setDiscussions(await resp.json());
      }
    } catch (e) {
      console.error("获取列表失败:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!topic.trim() || creating) return;
    setCreating(true);
    setError("");
    try {
      const resp = await fetch(`${API}/api/discussions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic.trim(), expert_count: expertCount }),
      });
      if (!resp.ok) throw new Error(`创建失败: ${resp.status}`);
      const data = await resp.json();
      navigate(`/lobby/${data.discussion_id}`);
    } catch (e) {
      setError(e.message);
      setCreating(false);
    }
  };

  const statusLabel = (s) => {
    const map = { pending: "查看阵容", in_progress: "观赛中", completed: "已回顾" };
    return map[s] || s;
  };

  const statusColor = (s) => {
    if (s === "in_progress") return "#10B981";
    if (s === "completed") return "#6B7280";
    return "#F59E0B";
  };

  return (
    <div className="home">
      <div className="home__header">
        <span className="home__logo">🎙</span>
        <h1 className="home__title">AI Panel Studio</h1>
        <p className="home__subtitle">智能圆桌讨论系统 — 输入话题，AI 专家自动辩论</p>
      </div>

      {/* 创建表单 */}
      <div className="home__create">
        <input
          className="home__input"
          placeholder="输入讨论话题，例如：AGI 是否应该暂停研发"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleCreate(); }}
        />
        <select
          className="home__select"
          value={expertCount}
          onChange={(e) => setExpertCount(Number(e.target.value))}
        >
          {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
            <option key={n} value={n}>{n} 位专家</option>
          ))}
        </select>
        <button
          className="home__btn"
          onClick={handleCreate}
          disabled={!topic.trim() || creating}
        >
          {creating ? "⏳ 创建中..." : "▶ 发起讨论"}
        </button>
        {error && <span className="home__error">{error}</span>}
      </div>

      {/* 讨论列表 */}
      <div className="home__list">
        <div className="home__list-header">
          <h2>讨论列表</h2>
          <span className="home__count">{discussions.length} 条记录</span>
        </div>

        {loading ? (
          <div className="home__loading">加载中...</div>
        ) : discussions.length === 0 ? (
          <div className="home__empty">
            <div className="home__empty-icon">🎬</div>
            <p>还没有讨论，输入话题开始第一个</p>
          </div>
        ) : (
          <div className="home__cards">
            {discussions.map((d) => (
              <div
                key={d.id}
                className="home__card"
                onClick={() => {
                  if (d.status === "pending") navigate(`/lobby/${d.id}`);
                  else navigate(`/studio/${d.id}`);
                }}
              >
                <div className="home__card-top">
                  <span className="home__card-topic">{d.topic}</span>
                  <span
                    className="home__card-status"
                    style={{
                      background: statusColor(d.status) + "22",
                      color: statusColor(d.status),
                      borderColor: statusColor(d.status),
                    }}
                  >
                    <span
                      className="home__status-dot"
                      style={{ background: statusColor(d.status) }}
                    />
                    {statusLabel(d.status)}
                  </span>
                </div>
                <div className="home__card-meta">
                  <span>{d.participant_count} 位参与者</span>
                  <span>{new Date(d.created_at).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default HomePage;
