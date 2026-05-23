"""
Partage Réseau & Notifications — La Péchouille
Helpers pour publier sur le fil et créer des notifications.
"""
from __future__ import annotations
from typing import Any
import streamlit as st
from core.supabase_client import supabase_get, supabase_post, supabase_patch


def _uid() -> str | None:
    u = st.session_state.get("reseau_user")
    return u["id"] if u else None


# ── PARTAGE ──────────────────────────────────────────────────────

def share_to_reseau(
    type_post:       str,
    ref_id:          int | None = None,
    contenu:         str = "",
    metadata:        dict | None = None,
    photo_url:       str = "",
    visibility:      str = "public",         # public | amis | prive
    allow_reshare:   bool = True,
    spot_precision:  str | None = None,      # exact | localite
    shared_from_id:  str | None = None,
) -> dict | None:
    """
    Publie un contenu sur le fil d'actualité.
    Retourne le post créé ou None.
    """
    uid = _uid()
    if not uid:
        return None

    data = {
        "user_id":        uid,
        "type":           type_post,
        "ref_id":         ref_id,
        "contenu":        contenu or "",
        "metadata":       metadata or {},
        "photo_url":      photo_url or "",
        "visibility":     visibility,
        "allow_reshare":  bool(allow_reshare),
    }
    if spot_precision:
        data["spot_precision"] = spot_precision
    if shared_from_id:
        data["shared_from_id"] = shared_from_id

    result = supabase_post("posts", data)

    # supabase_post peut retourner: list, dict, bool, ou None
    post = None
    if isinstance(result, list) and len(result) > 0:
        post = result[0]
    elif isinstance(result, dict):
        post = result
    elif result is True:
        # Insertion réussie mais sans return représentation
        post = {"id": None, **data}

    if post is None:
        st.error(f"Erreur Supabase. Réponse: {repr(result)[:200]}")
        return None

    # Si c'est un repartage, notif au créateur original
    if shared_from_id and post.get("id"):
        original = supabase_get("posts", {"id": f"eq.{shared_from_id}", "select": "user_id"})
        if original and original[0]["user_id"] != uid:
            notify(
                user_id=original[0]["user_id"],
                from_user_id=uid,
                type_notif="reshare",
                ref_type="post",
                ref_id=post["id"],
                message="a repartagé ta publication",
            )
    return post


def reshare_post(original_post_id: str, contenu: str = "",
                  visibility: str = "public") -> dict | None:
    """Repartage d'un post existant."""
    original = supabase_get("posts", {
        "id": f"eq.{original_post_id}",
        "select": "type,ref_id,metadata,photo_url,allow_reshare",
    })
    if not original or not original[0].get("allow_reshare"):
        return None

    o = original[0]
    return share_to_reseau(
        type_post=o["type"],
        ref_id=o.get("ref_id"),
        contenu=contenu,
        metadata=o.get("metadata") or {},
        photo_url=o.get("photo_url") or "",
        visibility=visibility,
        allow_reshare=False,  # on ne re-repartage pas
        shared_from_id=original_post_id,
    )


# ── FIL D'ACTUALITE ──────────────────────────────────────────────

def get_feed(limit: int = 50) -> list[dict]:
    """
    Retourne les posts visibles pour l'utilisateur courant :
    - public visible par tous
    - amis visible si on est ami avec l'auteur
    - prive visible seulement par l'auteur
    """
    uid = _uid()
    if not uid:
        # Pas connecté : seulement les posts publics
        return supabase_get("posts", {
            "visibility": "eq.public",
            "order":      "created_at.desc",
            "limit":      str(limit),
            "select":     "*",
        }) or []

    # Récupérer les amis acceptés
    amis_rows = supabase_get("amis", {
        "or":     f"(demandeur_id.eq.{uid},recepteur_id.eq.{uid})",
        "statut": "eq.accepte",
        "select": "demandeur_id,recepteur_id",
    }) or []
    ami_ids = set()
    for a in amis_rows:
        ami_ids.add(a["recepteur_id"] if a["demandeur_id"] == uid else a["demandeur_id"])

    # Récupérer beaucoup de posts puis filtrer côté Python (plus simple que OR complexe)
    raw = supabase_get("posts", {
        "order":  "created_at.desc",
        "limit":  str(limit * 2),
        "select": "*",
    }) or []

    visible = []
    for p in raw:
        v = p.get("visibility", "public")
        author = p.get("user_id")
        if v == "public":
            visible.append(p)
        elif v == "amis" and (author == uid or author in ami_ids):
            visible.append(p)
        elif v == "prive" and author == uid:
            visible.append(p)
        if len(visible) >= limit:
            break
    return visible


# ── NOTIFICATIONS ────────────────────────────────────────────────

def notify(
    user_id:      str,
    type_notif:   str,
    from_user_id: str | None = None,
    ref_type:     str | None = None,
    ref_id:       str | None = None,
    message:      str = "",
) -> None:
    """Crée une notification pour un utilisateur."""
    if user_id == from_user_id:
        return  # pas de notif à soi-même

    supabase_post("notifications", {
        "user_id":      user_id,
        "from_user_id": from_user_id,
        "type":         type_notif,
        "ref_type":     ref_type,
        "ref_id":       ref_id,
        "message":      message,
    })


def get_notifications(unread_only: bool = False, limit: int = 50) -> list[dict]:
    """Récupère les notifications de l'utilisateur courant."""
    uid = _uid()
    if not uid:
        return []

    params = {
        "user_id": f"eq.{uid}",
        "order":   "created_at.desc",
        "limit":   str(limit),
        "select":  "*",
    }
    if unread_only:
        params["lu"] = "eq.false"

    return supabase_get("notifications", params) or []


def count_unread_notifications() -> int:
    """Nombre de notifs non lues."""
    return len(get_notifications(unread_only=True, limit=100))


def mark_notification_read(notif_id: str) -> None:
    """Marque une notification comme lue."""
    supabase_patch("notifications", notif_id, {"lu": True})


def mark_all_notifications_read() -> None:
    """Marque toutes les notifs de l'utilisateur courant comme lues."""
    import requests
    from core.supabase_client import SUPABASE_URL, get_headers
    uid = _uid()
    if not uid: return
    requests.patch(
        f"{SUPABASE_URL}/rest/v1/notifications",
        headers={**get_headers(), "Prefer": "return=minimal"},
        params={"user_id": f"eq.{uid}", "lu": "eq.false"},
        json={"lu": True},
        timeout=5,
    )
