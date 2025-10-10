"""Tests for profile visibility filtering."""

from uuid import uuid4

from backend.app.schemas.users import ProfileSurvey, SharePreference, ShareScope
from backend.app.services.profile_privacy import Viewer, filter_profile_fields


def build_profile() -> ProfileSurvey:
    return ProfileSurvey(
        display_name="Test Disciple",
        bio="Follower of Christ",
        spiritual_background="Non-denominational",
        denominational_identity="Evangelical",
        study_focus_topics=["Grace", "Prayer"],
        study_rhythm="Morning devotions",
        guidance_preferences=["Gentle accountability"],
        preferred_translations=["ESV", "NIV"],
        prayer_interests=["Local church", "Family"],
        ai_journal_opt_in=True,
        share_preferences={
            "bio": SharePreference(scope=ShareScope.PUBLIC),
            "study_focus_topics": SharePreference(scope=ShareScope.CUSTOM, allowed_user_ids=[]),
            "prayer_interests": SharePreference(scope=ShareScope.PRIVATE),
        },
    )


def test_owner_can_view_all_sections():
    owner_id = uuid4()
    profile = build_profile()
    filtered, hidden = filter_profile_fields(
        owner_id=owner_id,
        profile=profile,
        share_prefs=profile.share_preferences,
        viewer=Viewer(user_id=owner_id, role="member"),
    )

    assert filtered == profile
    assert hidden == []


def test_public_and_private_rules_respected():
    owner_id = uuid4()
    profile = build_profile()
    viewer = Viewer(user_id=uuid4(), role="member")

    filtered, hidden = filter_profile_fields(
        owner_id=owner_id,
        profile=profile,
        share_prefs=profile.share_preferences,
        viewer=viewer,
    )

    assert filtered.bio == "Follower of Christ"  # public
    assert filtered.prayer_interests == []  # private hidden
    assert "prayer_interests" in hidden


def test_custom_visibility_allows_specific_user():
    owner_id = uuid4()
    allowed_viewer = uuid4()
    profile = build_profile()
    profile.share_preferences["study_focus_topics"] = SharePreference(
        scope=ShareScope.CUSTOM, allowed_user_ids=[allowed_viewer]
    )

    filtered, hidden = filter_profile_fields(
        owner_id=owner_id,
        profile=profile,
        share_prefs=profile.share_preferences,
        viewer=Viewer(user_id=allowed_viewer, role="member"),
    )

    assert filtered.study_focus_topics == ["Grace", "Prayer"]
    assert "study_focus_topics" not in hidden

    # Unapproved viewer should not see topics
    filtered_denied, hidden_denied = filter_profile_fields(
        owner_id=owner_id,
        profile=profile,
        share_prefs=profile.share_preferences,
        viewer=Viewer(user_id=uuid4(), role="member"),
    )

    assert filtered_denied.study_focus_topics == []
    assert "study_focus_topics" in hidden_denied


def test_admin_bypass():
    owner_id = uuid4()
    profile = build_profile()
    viewer = Viewer(user_id=uuid4(), role="admin")

    filtered, hidden = filter_profile_fields(
        owner_id=owner_id,
        profile=profile,
        share_prefs=profile.share_preferences,
        viewer=viewer,
    )

    assert filtered == profile
    assert hidden == []
