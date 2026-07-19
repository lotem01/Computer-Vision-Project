from app.domain.contracts import Keypoint
from app.services.exercise import compare_keypoints, normalized_pose


def point(name: str, x: float, y: float) -> Keypoint:
    return Keypoint(name=name, x=x, y=y, confidence=1, visible=True)


def simple_pose(offset_x=0.0, offset_y=0.0, scale=1.0):
    return [
        point("l_shoulder", offset_x + 0.4 * scale, offset_y + 0.3 * scale),
        point("r_shoulder", offset_x + 0.6 * scale, offset_y + 0.3 * scale),
        point("l_hip", offset_x + 0.42 * scale, offset_y + 0.55 * scale),
        point("r_hip", offset_x + 0.58 * scale, offset_y + 0.55 * scale),
        point("l_wrist", offset_x + 0.30 * scale, offset_y + 0.48 * scale),
        point("r_wrist", offset_x + 0.70 * scale, offset_y + 0.48 * scale),
    ]


def test_normalized_pose_is_resilient_to_camera_distance_and_offset():
    instructor = normalized_pose(simple_pose())
    user_farther = normalized_pose(simple_pose(offset_x=0.08, offset_y=0.12, scale=0.55))

    assert abs(instructor["l_wrist"][0] - user_farther["l_wrist"][0]) < 0.001
    assert abs(instructor["r_wrist"][1] - user_farther["r_wrist"][1]) < 0.001


def test_compare_keypoints_marks_far_joint_for_feedback():
    instructor = simple_pose()
    user = simple_pose()
    user[-1] = point("r_wrist", 0.55, 0.78)

    score, feedback = compare_keypoints(instructor, user)
    by_name = {item.name: item for item in feedback}

    assert score < 100
    assert by_name["l_wrist"].close is True
    assert by_name["r_wrist"].close is False
