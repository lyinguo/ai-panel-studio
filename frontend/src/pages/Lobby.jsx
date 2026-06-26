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
  const [selectedIds, setSelectedIds] = useState(new Set());
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
      if (data.status === "in_progress" || data.status === "completed") {
        navigate(`/studio/${id}`); return;
      }
    } catch (e) {
      navigate("/");
    } finally {
      setLoading(false);
    }
  };

  // 初始化默认选中：主持人 + 前 expert_count 位专家
  useEffect(() => {
    if (participants.length > 0) {
      const host = participants.find((p) => p.role === "host");
      const experts = participants.filter((p) => p.role === "expert");
      // 默认选主持人 + 所有专家（用户可以取消不需要的）
      const ids = new Set([host.id, ...experts.map((e) => e.id)]);
      setSelectedIds(ids);
    }
  }, [participants]);

  const toggleExpert = (pid) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(pid)) next.delete(pid);
      else next.add(pid);
      return next;
    });
  };

  const selectedCount = participants.filter((p) => p.role === "expert" && selectedIds.has(p.id)).length;

  const handleConfirm = async () => {
    if (starting || selectedCount < 1) return;
    setStarting(true);
    setError("");
    try {
      const body = { participant_ids: [...selectedIds] };
      const resp = await fetch(`${API}/api/discussions/${id}/start`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
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
    return <div className="lobby"><div className="lobby__loading">加载讨论阵容中...</div></div>;
  }

  const host = participants.find((p) => p.role === "host");
  const experts = participants.filter((p) => p.role === "expert");
  const selectedExperts = experts.filter((p) => selectedIds.has(p.id));
  const candidateExperts = experts.filter((p) => !selectedIds.has(p.id));

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

      {/* 已选专家 */}
      <div className="lobby__section">
        <h2 className="lobby__section-title">
          已选专家
          <span className="lobby__count">{selectedExperts.length} 位</span>
        </h2>
        {selectedExperts.length > 0 ? (
          <div className="lobby__grid">
            {selectedExperts.map((p) => (
              <div
                key={p.id}
                className="lobby__card lobby__card--selectable lobby__card--selected"
                style={{ borderLeftColor: p.color_code }}
                onClick={() => toggleExpert(p.id)}
              >
                <div className="lobby__checkbox">
                  <span className="lobby__checkmark lobby__checkmark--on"
                    style={{ backgroundColor: p.color_code, borderColor: p.color_code }}>
                    ✓
                  </span>
                </div>
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
        ) : (
          <p className="lobby__hint" style={{ padding: '12px 0' }}>暂未选择专家，请从候补区添加</p>
        )}
      </div>

      {/* 候补区 */}
      {candidateExperts.length > 0 && (
        <div className="lobby__section">
          <h2 className="lobby__section-title">
            候补专家
            <span className="lobby__count">{candidateExperts.length} 位候选</span>
          </h2>
          <p className="lobby__hint">点击候补专家可将其加入阵容</p>
          <div className="lobby__grid">
            {candidateExperts.map((p) => (
              <div
                key={p.id}
                className="lobby__card lobby__card--selectable lobby__card--unselected"
                onClick={() => toggleExpert(p.id)}
              >
                <div className="lobby__checkbox">
                  <span className="lobby__checkmark">+</span>
                </div>
                <div className="lobby__avatar" style={{ borderColor: p.color_code, opacity: 0.5 }}>
                  <span style={{ color: p.color_code }}>{p.name[0]}</span>
                </div>
                <div className="lobby__info" style={{ opacity: 0.5 }}>
                  <div className="lobby__name-row">
                    <span className="lobby__name" style={{ color: p.color_code }}>{p.name}</span>
                    <span className="lobby__role-tag">候补</span>
                  </div>
                  <div className="lobby__title-text">{p.title}</div>
                  <div className="lobby__stance">{p.stance}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 确认按钮 */}
      <div className="lobby__actions">
        {error && <p className="lobby__error">{error}</p>}
        {selectedCount < 1 && (
          <p className="lobby__error">请至少选择 1 位专家</p>
        )}
        <button
          className="lobby__btn"
          onClick={handleConfirm}
          disabled={starting || selectedCount < 1}
        >
          {starting ? "⏳ 启动中..." : `✅ 确认 ${selectedCount} 位专家，进入演播厅`}
        </button>
        <button className="lobby__btn-ghost" onClick={() => navigate("/")}>取消，返回首页</button>
      </div>
    </div>
  );
}

export default Lobby;