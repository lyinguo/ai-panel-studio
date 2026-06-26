import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

const API = "http://localhost:8000";

function Lobby() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [participants, setParticipants] = useState([]);
  const [topic, setTopic] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDiscussion();
  }, [id]);

  const fetchDiscussion = async () => {
    try {
      const resp = await fetch(`${API}/api/discussions/${id}`);
      if (!resp.ok) { navigate("/"); return; }
      const data = await resp.json();
      setTopic(data.topic);
      setStatus(data.status);
      setParticipants(data.participants || []);
      // 已开始或已结束 → 直接进演播厅
      if (data.status === "in_progress" || data.status === "completed") {
        navigate(`/studio/${id}`); return;
      }
    } catch (e) {
      console.error("加载讨论失败:", e);
      navigate("/");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (starting) return;
    setStarting(true);
    setError("");
    try {
      const resp = await fetch(`${API}/api/discussions/${id}/start`, { method: "PUT" });
      if (!resp.ok) {
        const msg = await resp.json();
        throw new Error(msg.detail || "启动失败");
      }
      navigate(`/studio/${id}`);
    } catch (e) {
      setError(e.message);
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <div className="lobby">
        <div className="lobby__loading">加载讨论阵容中...</div>
      </div>
    );
  }

  const host = participants.find((p) => p.role === "host");
  const experts = participants.filter((p) => p.role === "expert");

  return (
    <div className="lobby">
      <div className="lobby__header">
        <button className="lobby__back" onClick={() => navigate("/")}>← 返回</button>
        <h1 className="lobby__title">🎙 确认讨论阵容</h1>
        <p className="lobby__topic">话题：{topic}</p>
      </div>

      {/* 主持人 */}
      {host && (
        <div className="lobby__section">
          <h2 className="lobby__section-title">主持人</h2>
          <div className="lobby__card lobby__card--host">
            <div className="lobby__avatar" style={{ borderColor: host.color_code }}>
              <span style={{ color: host.color_code }}>{host.name[0]}</span>
            </div>
            <div className="lobby__info">
              <div className="lobby__name-row">
                <span className="lobby__name" style={{ color: host.color_code }}>{host.name}</span>
                <span className="lobby__role-tag">主持人</span>
              </div>
              <div className="lobby__title-text">{host.title}</div>
              <div className="lobby__stance">{host.stance}</div>
            </div>
          </div>
        </div>
      )}

      {/* 专家团 */}
      <div className="lobby__section">
        <h2 className="lobby__section-title">专家团 <span className="lobby__count">{experts.length} 位</span></h2>
        <div className="lobby__grid">
          {experts.map((p) => (
            <div key={p.id} className="lobby__card" style={{ borderLeftColor: p.color_code }}>
              <div className="lobby__avatar" style={{ borderColor: p.color_code }}>
                <span style={{ color: p.color_code }}>{p.name[0]}</span>
              </div>
              <div className="lobby__info">
                <div className="lobby__name-row">
                  <span className="lobby__name" style={{ color: p.color_code }}>{p.name}</span>
                  <span className="lobby__role-tag">专家</span>
                </div>
                <div className="lobby__title-text">{p.title}</div>
                <div className="lobby__stance">{p.stance}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 确认按钮 */}
      <div className="lobby__actions">
        {error && <p className="lobby__error">{error}</p>}
        <button
          className="lobby__btn"
          onClick={handleConfirm}
          disabled={starting}
        >
          {starting ? "⏳ 启动中..." : "✅ 确认阵容，进入演播厅"}
        </button>
        <button className="lobby__btn-ghost" onClick={() => navigate("/")}>
          取消，返回首页
        </button>
      </div>
    </div>
  );
}

export default Lobby;