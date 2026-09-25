from __future__ import annotations

from datetime import datetime, timezone, timedelta
import streamlit as st

from utils.auth import authenticated_client, current_user, has_permission


def fetch_active_priorities():
    if not has_permission("prioridades", "view"):
        return []
    client = authenticated_client()
    if not client:
        return []
    try:
        resp = client.table("app_priorities").select("*").eq("active", True).order("priority_level", desc=True).execute()
        return resp.data or []
    except Exception:
        return []


def _due(row):
    value = row.get("reminder_at")
    if not value:
        return True
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt <= datetime.now(timezone.utc)
    except Exception:
        return True


def show_priority_notifications():
    if not has_permission("prioridades", "view"):
        return
    user = current_user()
    uid = user.get("id")
    if not uid:
        return
    client = authenticated_client()
    for row in fetch_active_priorities()[:8]:
        if not _due(row):
            continue
        repeat = int(row.get("repeat_minutes") or 60)
        try:
            rr = client.table("app_priority_notifications").select("last_seen_at").eq("priority_id", row["id"]).eq("user_id", uid).limit(1).execute()
            last = (rr.data or [{}])[0].get("last_seen_at") if rr.data else None
            if last:
                last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) < last_dt + timedelta(minutes=max(repeat, 1)):
                    continue
        except Exception:
            pass
        icon = "🚨" if row.get("priority_level") == "urgente" else "⭐"
        st.toast(f"{row.get('title', 'Prioridad')}\n{row.get('description') or ''}", icon=icon)
        try:
            client.table("app_priority_notifications").upsert({
                "priority_id": row["id"], "user_id": uid,
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
            }, on_conflict="priority_id,user_id").execute()
        except Exception:
            pass
