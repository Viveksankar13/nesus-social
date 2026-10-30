"""
Social Features and Authorization Test Suite
============================================
Comprehensive test suite verifying:
- SOCIAL-01: User profiles, editing, stats, and password changing
- SOCIAL-02: Post creation, editing, and deletion
- SOCIAL-03: Post length and content validation (<= 1000 chars)
- SOCIAL-04: Keyset cursor pagination and feed filtering (all vs mine)
- SOCIAL-05: Like toggle, atomic counter updates, and notifications
- SOCIAL-06: Threaded comments and strict 1-level reply enforcement
- QUAL-02: Granular authorization and ownership enforcement (User vs Admin)
"""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification

# ── SOCIAL-02 & SOCIAL-03: Post Creation and Validation ──────────────────────


@pytest.mark.asyncio
async def test_create_post_success(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Test creating a post with valid content and image URL."""
    user, headers = await create_user(username="author1", email="author1@example.com")

    payload = {
        "content": "Hello Nexus Social! This is my first post.",
        "image_url": "https://images.unsplash.com/photo-1",
    }
    response = await client.post("/api/v1/posts", json=payload, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["content"] == payload["content"]
    assert data["image_url"] == payload["image_url"]
    assert data["author"]["username"] == "author1"
    assert data["likes_count"] == 0
    assert data["comments_count"] == 0
    assert data["has_liked"] is False
    assert data["is_edited"] is False


@pytest.mark.asyncio
async def test_post_length_and_whitespace_validation(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Validate 1000 character limit and rejection of empty/whitespace content."""
    _, headers = await create_user(username="validator", email="val@example.com")

    # 1000 characters: valid
    max_content = "a" * 1000
    res_valid = await client.post(
        "/api/v1/posts",
        json={"content": max_content},
        headers=headers,
    )
    assert res_valid.status_code == 201

    # 1001 characters: rejected with 422
    too_long = "a" * 1001
    res_too_long = await client.post(
        "/api/v1/posts",
        json={"content": too_long},
        headers=headers,
    )
    assert res_too_long.status_code == 422

    # Whitespace only: rejected with 422
    res_empty = await client.post(
        "/api/v1/posts",
        json={"content": "    "},
        headers=headers,
    )
    assert res_empty.status_code == 422


# ── SOCIAL-02 & QUAL-02: Post Updates, Deletions, and Authorization ──────────


@pytest.mark.asyncio
async def test_update_own_post(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Test author editing their own post."""
    _, headers = await create_user(username="editor", email="editor@example.com")

    create_res = await client.post(
        "/api/v1/posts",
        json={"content": "Original draft."},
        headers=headers,
    )
    post_id = create_res.json()["id"]

    edit_res = await client.put(
        f"/api/v1/posts/{post_id}",
        json={"content": "Edited published version."},
        headers=headers,
    )
    assert edit_res.status_code == 200
    data = edit_res.json()
    assert data["content"] == "Edited published version."
    assert data["is_edited"] is True


@pytest.mark.asyncio
async def test_post_authorization_edit_and_delete(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """
    Test that regular users cannot edit or delete another user's post,
    but administrators can perform both actions.
    """
    owner, owner_headers = await create_user(username="owner", email="owner@example.com")
    _, stranger_headers = await create_user(username="stranger", email="stranger@example.com")
    _, admin_headers = await create_user(
        username="admin_user", email="admin2@example.com", role="admin"
    )

    # Owner creates post
    post_res = await client.post(
        "/api/v1/posts",
        json={"content": "Protected post."},
        headers=owner_headers,
    )
    post_id = post_res.json()["id"]

    # Stranger attempts edit -> 403 Forbidden
    stranger_edit = await client.put(
        f"/api/v1/posts/{post_id}",
        json={"content": "Hacked content!"},
        headers=stranger_headers,
    )
    assert stranger_edit.status_code == 403

    # Stranger attempts delete -> 403 Forbidden
    stranger_del = await client.delete(
        f"/api/v1/posts/{post_id}",
        headers=stranger_headers,
    )
    assert stranger_del.status_code == 403

    # Admin edits post -> 200 OK
    admin_edit = await client.put(
        f"/api/v1/posts/{post_id}",
        json={"content": "Moderated by administrator."},
        headers=admin_headers,
    )
    assert admin_edit.status_code == 200
    assert admin_edit.json()["content"] == "Moderated by administrator."

    # Admin deletes post -> 204 No Content
    admin_del = await client.delete(
        f"/api/v1/posts/{post_id}",
        headers=admin_headers,
    )
    assert admin_del.status_code == 204

    # Verify post is gone -> 404
    get_res = await client.get(f"/api/v1/posts/{post_id}")
    assert get_res.status_code == 404


# ── SOCIAL-04: Keyset Cursor Pagination and Feed Filtering ───────────────────


@pytest.mark.asyncio
async def test_cursor_feed_pagination_and_filtering(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Test keyset cursor pagination with limit and feed filtering."""
    user_a, headers_a = await create_user(username="feed_a", email="fa@example.com")
    user_b, headers_b = await create_user(username="feed_b", email="fb@example.com")

    # User A creates 3 posts
    for i in range(3):
        await client.post(
            "/api/v1/posts",
            json={"content": f"Post A {i}"},
            headers=headers_a,
        )

    # User B creates 2 posts
    for j in range(2):
        await client.post(
            "/api/v1/posts",
            json={"content": f"Post B {j}"},
            headers=headers_b,
        )

    # Page 1 of all posts (limit=2)
    page1_res = await client.get("/api/v1/posts?limit=2")
    assert page1_res.status_code == 200
    page1 = page1_res.json()
    assert len(page1["items"]) == 2
    assert page1["has_more"] is True
    assert page1["next_cursor"] is not None

    # Page 2 using cursor (limit=2)
    cursor1 = page1["next_cursor"]
    page2_res = await client.get(f"/api/v1/posts?limit=2&cursor={cursor1}")
    assert page2_res.status_code == 200
    page2 = page2_res.json()
    assert len(page2["items"]) == 2
    assert page2["has_more"] is True

    # Page 3 using cursor (remaining 1 post)
    cursor2 = page2["next_cursor"]
    page3_res = await client.get(f"/api/v1/posts?limit=2&cursor={cursor2}")
    assert page3_res.status_code == 200
    page3 = page3_res.json()
    assert len(page3["items"]) == 1
    assert page3["has_more"] is False
    assert page3["next_cursor"] is None

    # Test "mine" feed filter
    mine_res = await client.get(
        "/api/v1/posts?feed_type=mine",
        headers=headers_b,
    )
    assert mine_res.status_code == 200
    mine_data = mine_res.json()
    assert len(mine_data["items"]) == 2
    for item in mine_data["items"]:
        assert item["author"]["username"] == "feed_b"


# ── SOCIAL-05: Like Toggle and Notifications ─────────────────────────────────


@pytest.mark.asyncio
async def test_like_toggle_and_notifications(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Test like toggle and persistent notification dispatch."""
    author, author_headers = await create_user(username="author_like", email="al@example.com")
    liker, liker_headers = await create_user(username="liker", email="liker@example.com")

    # Author creates a post
    post_res = await client.post(
        "/api/v1/posts",
        json={"content": "Like me!"},
        headers=author_headers,
    )
    post_id = post_res.json()["id"]

    # Liker likes the post
    like_res1 = await client.post(f"/api/v1/posts/{post_id}/like", headers=liker_headers)
    assert like_res1.status_code == 200
    assert like_res1.json()["liked"] is True
    assert like_res1.json()["likes_count"] == 1

    # Check notification persisted for author
    notif_stmt = select(Notification).where(
        Notification.user_id == author.id,
        Notification.type == "like",
    )
    notif = (await test_db_session.execute(notif_stmt)).scalar_one_or_none()
    assert notif is not None
    assert notif.payload["post_id"] == post_id
    assert notif.payload["liker_username"] == "liker"

    # Liker unlikes the post
    like_res2 = await client.post(f"/api/v1/posts/{post_id}/like", headers=liker_headers)
    assert like_res2.status_code == 200
    assert like_res2.json()["liked"] is False
    assert like_res2.json()["likes_count"] == 0


# ── SOCIAL-06: Comments and 1-Level Nested Replies ───────────────────────────


@pytest.mark.asyncio
async def test_comments_and_one_level_replies(
    client: AsyncClient,
    create_user: Callable[..., Any],
    test_db_session: AsyncSession,
) -> None:
    """Test top-level comment, 1-level reply, and rejection of 2nd-level reply."""
    post_author, author_headers = await create_user(username="c_author", email="ca@example.com")
    commenter, comm_headers = await create_user(username="commenter", email="comm@example.com")
    replier, replier_headers = await create_user(username="replier", email="rep@example.com")

    # Author creates post
    post_res = await client.post(
        "/api/v1/posts",
        json={"content": "Discussion post."},
        headers=author_headers,
    )
    post_id = post_res.json()["id"]

    # Top-level comment
    comm_res = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Top-level comment."},
        headers=comm_headers,
    )
    assert comm_res.status_code == 201
    top_comment_id = comm_res.json()["id"]
    assert comm_res.json()["parent_id"] is None

    # Verify notification for post author
    notif_post_author = (
        await test_db_session.execute(
            select(Notification).where(
                Notification.user_id == post_author.id,
                Notification.type == "comment",
            )
        )
    ).scalar_one_or_none()
    assert notif_post_author is not None

    # 1-level reply to top comment
    reply_res = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Reply to top-level.", "parent_id": top_comment_id},
        headers=replier_headers,
    )
    assert reply_res.status_code == 201
    reply_id = reply_res.json()["id"]
    assert reply_res.json()["parent_id"] == top_comment_id

    # Verify notification for comment author (reply notification)
    notif_comment_author = (
        await test_db_session.execute(
            select(Notification).where(
                Notification.user_id == commenter.id,
                Notification.type == "reply",
            )
        )
    ).scalar_one_or_none()
    assert notif_comment_author is not None

    # Attempt 2nd level reply (replying to a reply) -> rejected with 400
    invalid_nested_res = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "Nested reply attempt.", "parent_id": reply_id},
        headers=author_headers,
    )
    assert invalid_nested_res.status_code == 400
    assert "Nested replies beyond 1 level are not allowed" in invalid_nested_res.json()["detail"]

    # Verify threaded comments response structure
    comments_list_res = await client.get(f"/api/v1/posts/{post_id}/comments")
    assert comments_list_res.status_code == 200
    comments_tree = comments_list_res.json()
    assert len(comments_tree) == 1
    assert comments_tree[0]["id"] == top_comment_id
    assert len(comments_tree[0]["replies"]) == 1
    assert comments_tree[0]["replies"][0]["id"] == reply_id


# ── SOCIAL-01: Profiles and Password Changes ─────────────────────────────────


@pytest.mark.asyncio
async def test_user_profiles_and_password_changes(
    client: AsyncClient,
    create_user: Callable[..., Any],
) -> None:
    """Test retrieving profile, updating bio/location, and changing password."""
    user, headers = await create_user(
        username="profile_user",
        email="prof@example.com",
        password="OldPassword123!",
    )

    # View by username
    prof_res = await client.get("/api/v1/users/profile_user")
    assert prof_res.status_code == 200
    data = prof_res.json()
    assert data["username"] == "profile_user"
    assert data["posts_count"] == 0

    # View by UUID
    prof_uuid_res = await client.get(f"/api/v1/users/{user.id}")
    assert prof_uuid_res.status_code == 200

    # Update own profile
    update_res = await client.put(
        "/api/v1/users/me",
        json={
            "bio": "AI engineer & open-source builder",
            "location": "San Francisco, CA",
            "website": "https://example.com",
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["bio"] == "AI engineer & open-source builder"
    assert updated_data["location"] == "San Francisco, CA"
    assert updated_data["website"] == "https://example.com"

    # Change password: wrong current password
    bad_pw_res = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "WrongPassword1!", "new_password": "NewValidPass123!"},
        headers=headers,
    )
    assert bad_pw_res.status_code == 400

    # Change password: valid
    good_pw_res = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "OldPassword123!", "new_password": "NewValidPass123!"},
        headers=headers,
    )
    assert good_pw_res.status_code == 200
    assert "Password changed successfully" in good_pw_res.json()["message"]
