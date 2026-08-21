import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

SCHEMA_URL = (
    "https://schema.getpostman.com/json/"
    "collection/v2.1.0/collection.json"
)


def raw_body(payload):
    return {
        "mode": "raw",
        "raw": json.dumps(payload, indent=2),
        "options": {
            "raw": {
                "language": "json",
            }
        },
    }


def form_body(fields):
    formdata = []

    for key, value, field_type in fields:
        item = {
            "key": key,
            "type": field_type,
        }

        if field_type == "file":
            item["src"] = []
        else:
            item["value"] = value

        formdata.append(item)

    return {
        "mode": "formdata",
        "formdata": formdata,
    }


def status_test(expected_status):
    return [
        (
            f'pm.test("Status is {expected_status}", '
            "function () {"
        ),
        (
            f"    pm.response.to.have.status"
            f"({expected_status});"
        ),
        "});",
    ]


def request_item(
    name,
    method,
    path,
    *,
    body=None,
    formdata=None,
    bearer=None,
    tests=None,
    description=None,
):
    headers = []

    if body is not None:
        headers.append(
            {
                "key": "Content-Type",
                "value": "application/json",
                "type": "text",
            }
        )

    request = {
        "method": method,
        "header": headers,
        "url": f"{{{{baseUrl}}}}{path}",
    }

    if bearer:
        request["auth"] = {
            "type": "bearer",
            "bearer": [
                {
                    "key": "token",
                    "value": f"{{{{{bearer}}}}}",
                    "type": "string",
                }
            ],
        }
    else:
        request["auth"] = {"type": "noauth"}

    if body is not None:
        request["body"] = raw_body(body)

    if formdata is not None:
        request["body"] = form_body(formdata)

    if description:
        request["description"] = description

    item = {
        "name": name,
        "request": request,
    }

    if tests:
        item["event"] = [
            {
                "listen": "test",
                "script": {
                    "type": "text/javascript",
                    "exec": tests,
                },
            }
        ]

    return item


def folder(name, items):
    return {
        "name": name,
        "item": items,
    }


class Command(BaseCommand):
    help = "Export the DevFolio Postman collection."

    def handle(self, *args, **options):
        login_tests = status_test(200) + [
            "const data = pm.response.json();",
            (
                'pm.collectionVariables.set('
                '"accessToken", data.access);'
            ),
            (
                'pm.collectionVariables.set('
                '"refreshToken", data.refresh);'
            ),
        ]

        collection = {
            "info": {
                "name": "DevFolio Portfolio API",
                "description": (
                    "Complete API collection for the DevFolio "
                    "Django REST Framework backend."
                ),
                "schema": SCHEMA_URL,
            },
            "event": [
                {
                    "listen": "prerequest",
                    "script": {
                        "type": "text/javascript",
                        "exec": [
                            (
                                "if (!pm.collectionVariables.get"
                                '("visitorId")) {'
                            ),
                            (
                                "    pm.collectionVariables.set("
                                '"visitorId", '
                                'pm.variables.replaceIn("{{$guid}}"));'
                            ),
                            "}",
                        ],
                    },
                }
            ],
            "variable": [
                {
                    "key": "baseUrl",
                    "value": "http://127.0.0.1:8000/api",
                },
                {"key": "username", "value": ""},
                {"key": "password", "value": ""},
                {"key": "newPassword", "value": ""},
                {"key": "accessToken", "value": ""},
                {"key": "refreshToken", "value": ""},
                {"key": "normalAccessToken", "value": ""},
                {"key": "visitorId", "value": ""},
                {"key": "skillId", "value": ""},
                {"key": "experienceId", "value": ""},
                {"key": "educationId", "value": ""},
                {"key": "projectSlug", "value": ""},
                {"key": "categoryId", "value": ""},
                {"key": "categorySlug", "value": ""},
                {"key": "tagId", "value": ""},
                {"key": "tagSlug", "value": ""},
                {"key": "postSlug", "value": ""},
                {"key": "draftSlug", "value": ""},
                {"key": "commentId", "value": ""},
                {"key": "contactId", "value": ""},
            ],
            "item": [
                folder(
                    "01 - Authentication",
                    [
                        request_item(
                            "Owner login",
                            "POST",
                            "/auth/login/",
                            body={
                                "username": "{{username}}",
                                "password": "{{password}}",
                            },
                            tests=login_tests,
                        ),
                        request_item(
                            "Refresh access token",
                            "POST",
                            "/auth/refresh/",
                            body={
                                "refresh": "{{refreshToken}}",
                            },
                            tests=status_test(200),
                        ),
                        request_item(
                            "Current owner",
                            "GET",
                            "/auth/me/",
                            bearer="accessToken",
                            tests=status_test(200),
                        ),
                    ],
                ),
                folder(
                    "02 - Profile",
                    [
                        request_item(
                            "Get public profile",
                            "GET",
                            "/profile/",
                            tests=status_test(200),
                        ),
                        request_item(
                            "Update owner profile",
                            "PATCH",
                            "/profile/",
                            bearer="accessToken",
                            body={
                                "headline": (
                                    "Full-Stack Django Developer"
                                ),
                                "is_available_for_hire": True,
                            },
                            tests=status_test(200),
                        ),
                    ],
                ),
                folder(
                    "03 - Skills",
                    [
                        request_item(
                            "List and filter skills",
                            "GET",
                            (
                                "/skills/?category=BACKEND"
                                "&is_featured=true"
                                "&search=python"
                                "&ordering=-proficiency"
                            ),
                            tests=status_test(200),
                        ),
                        request_item(
                            "Create skill",
                            "POST",
                            "/skills/",
                            bearer="accessToken",
                            body={
                                "name": (
                                    "Postman Skill {{$timestamp}}"
                                ),
                                "category": "BACKEND",
                                "proficiency": 90,
                                "icon": "python",
                                "display_order": 1,
                                "is_featured": True,
                            },
                            tests=status_test(201) + [
                                "const data = pm.response.json();",
                                (
                                    "pm.collectionVariables.set("
                                    '"skillId", data.id);'
                                ),
                            ],
                        ),
                    ],
                ),
                folder(
                    "04 - Experience and Education",
                    [
                        request_item(
                            "List experiences",
                            "GET",
                            "/experiences/",
                            tests=status_test(200),
                        ),
                        request_item(
                            "Create experience",
                            "POST",
                            "/experiences/",
                            bearer="accessToken",
                            body={
                                "company": "Postman Test Company",
                                "role": "Backend Developer",
                                "employment_type": "FULL_TIME",
                                "location": "Dhaka",
                                "start_date": "2024-01-01",
                                "end_date": None,
                                "is_current": True,
                                "description": (
                                    "Temporary API test record."
                                ),
                                "company_url": (
                                    "https://example.com"
                                ),
                                "display_order": 1,
                            },
                            tests=status_test(201) + [
                                "const data = pm.response.json();",
                                (
                                    "pm.collectionVariables.set("
                                    '"experienceId", data.id);'
                                ),
                            ],
                        ),
                        request_item(
                            "List education",
                            "GET",
                            "/education/",
                            tests=status_test(200),
                        ),
                        request_item(
                            "Create education",
                            "POST",
                            "/education/",
                            bearer="accessToken",
                            body={
                                "institution": (
                                    "Postman Test Institute"
                                ),
                                "degree": "Certificate",
                                "field_of_study": (
                                    "Web Development"
                                ),
                                "start_year": 2024,
                                "end_year": 2025,
                                "grade": "",
                                "description": (
                                    "Temporary API test record."
                                ),
                            },
                            tests=status_test(201) + [
                                "const data = pm.response.json();",
                                (
                                    "pm.collectionVariables.set("
                                    '"educationId", data.id);'
                                ),
                            ],
                        ),
                    ],
                ),
                folder(
                    "05 - Categories and Tags",
                    [
                        request_item(
                            "List categories",
                            "GET",
                            "/categories/",
                            tests=status_test(200),
                        ),
                        request_item(
                            "Create category",
                            "POST",
                            "/categories/",
                            bearer="accessToken",
                            body={
                                "name": (
                                    "Postman Category {{$timestamp}}"
                                ),
                                "description": (
                                    "Temporary test category."
                                ),
                            },
                            tests=status_test(201) + [
                                "const data = pm.response.json();",
                                (
                                    "pm.collectionVariables.set("
                                    '"categoryId", data.id);'
                                ),
                                (
                                    "pm.collectionVariables.set("
                                    '"categorySlug", data.slug);'
                                ),
                            ],
                        ),
                        request_item(
                            "List tags",
                            "GET",
                            "/tags/",
                            tests=status_test(200),
                        ),
                        request_item(
                            "Create tag",
                            "POST",
                            "/tags/",
                            bearer="accessToken",
                            body={
                                "name": (
                                    "Postman Tag {{$timestamp}}"
                                ),
                            },
                            tests=status_test(201) + [
                                "const data = pm.response.json();",
                                (
                                    "pm.collectionVariables.set("
                                    '"tagId", data.id);'
                                ),
                                (
                                    "pm.collectionVariables.set("
                                    '"tagSlug", data.slug);'
                                ),
                            ],
                        ),
                    ],
                ),
                folder(
                    "06 - Projects",
                    [
                        request_item(
                            "Create project",
                            "POST",
                            "/projects/",
                            bearer="accessToken",
                            formdata=[
                                (
                                    "title",
                                    (
                                        "Postman Project "
                                        "{{$timestamp}}"
                                    ),
                                    "text",
                                ),
                                (
                                    "summary",
                                    "Project created from Postman.",
                                    "text",
                                ),
                                (
                                    "description",
                                    (
                                        "Temporary project used to "
                                        "verify the API collection."
                                    ),
                                    "text",
                                ),
                                (
                                    "cover_image",
                                    "",
                                    "file",
                                ),
                                (
                                    "tech_stack",
                                    "{{skillId}}",
                                    "text",
                                ),
                                ("category", "API", "text"),
                                (
                                    "live_url",
                                    "",
                                    "text",
                                ),
                                (
                                    "github_url",
                                    (
                                        "https://github.com/"
                                        "example/postman-project"
                                    ),
                                    "text",
                                ),
                                (
                                    "is_featured",
                                    "true",
                                    "text",
                                ),
                                (
                                    "completed_date",
                                    "2025-01-01",
                                    "text",
                                ),
                                (
                                    "display_order",
                                    "1",
                                    "text",
                                ),
                            ],
                            description=(
                                "Select a JPG/PNG/WEBP file under "
                                "cover_image before sending."
                            ),
                            tests=status_test(201) + [
                                "const data = pm.response.json();",
                                (
                                    "pm.collectionVariables.set("
                                    '"projectSlug", data.slug);'
                                ),
                            ],
                        ),
                        request_item(
                            "List and filter projects",
                            "GET",
                            (
                                "/projects/?category=API"
                                "&tech={{skillId}}"
                                "&ordering=-completed_date"
                            ),
                            tests=status_test(200),
                        ),
                        request_item(
                            "Get project by slug",
                            "GET",
                            "/projects/{{projectSlug}}/",
                            tests=status_test(200),
                        ),
                    ],
                ),
                folder(
                    "07 - Blog Posts",
                    [
                        request_item(
                            "Create published post",
                            "POST",
                            "/posts/",
                            bearer="accessToken",
                            formdata=[
                                (
                                    "title",
                                    (
                                        "Postman Article "
                                        "{{$timestamp}}"
                                    ),
                                    "text",
                                ),
                                (
                                    "excerpt",
                                    (
                                        "Article created through "
                                        "the Postman collection."
                                    ),
                                    "text",
                                ),
                                (
                                    "content",
                                    (
                                        "This is substantial original "
                                        "test content for validating "
                                        "the Django REST Framework "
                                        "post creation endpoint. It is "
                                        "longer than one hundred "
                                        "characters as required."
                                    ),
                                    "text",
                                ),
                                (
                                    "cover_image",
                                    "",
                                    "file",
                                ),
                                (
                                    "category",
                                    "{{categoryId}}",
                                    "text",
                                ),
                                (
                                    "tags",
                                    "{{tagId}}",
                                    "text",
                                ),
                                (
                                    "status",
                                    "PUBLISHED",
                                    "text",
                                ),
                                (
                                    "is_featured",
                                    "true",
                                    "text",
                                ),
                            ],
                            description=(
                                "Select a JPG/PNG/WEBP file under "
                                "cover_image before sending."
                            ),
                            tests=status_test(201) + [
                                "const data = pm.response.json();",
                                (
                                    "pm.collectionVariables.set("
                                    '"postSlug", data.slug);'
                                ),
                            ],
                        ),
                        request_item(
                            "List published posts",
                            "GET",
                            (
                                "/posts/?category={{categorySlug}}"
                                "&tag={{tagSlug}}"
                                "&ordering=-published_at"
                            ),
                            tests=status_test(200),
                        ),
                        request_item(
                            "Search posts",
                            "GET",
                            "/posts/?search=django",
                            tests=status_test(200),
                        ),
                        request_item(
                            "Get post detail",
                            "GET",
                            "/posts/{{postSlug}}/",
                            tests=status_test(200),
                        ),
                        request_item(
                            "List owner drafts",
                            "GET",
                            "/posts/?status=DRAFT",
                            bearer="accessToken",
                            tests=status_test(200),
                        ),
                    ],
                ),
                folder(
                    "08 - Likes and Comments",
                    [
                        request_item(
                            "Toggle post like",
                            "POST",
                            "/posts/{{postSlug}}/like/",
                            tests=status_test(200),
                        ),
                        request_item(
                            "List approved threaded comments",
                            "GET",
                            "/posts/{{postSlug}}/comments/",
                            tests=status_test(200),
                        ),
                        request_item(
                            "Submit pending comment",
                            "POST",
                            "/posts/{{postSlug}}/comments/",
                            body={
                                "name": "Postman Visitor",
                                "email": "visitor@example.com",
                                "website": "",
                                "content": (
                                    "A valid comment submitted "
                                    "through Postman."
                                ),
                            },
                            tests=status_test(201) + [
                                "const data = pm.response.json();",
                                (
                                    "pm.collectionVariables.set("
                                    '"commentId", data.comment_id);'
                                ),
                            ],
                        ),
                        request_item(
                            "List pending comments as owner",
                            "GET",
                            (
                                "/comments/?is_approved=false"
                                "&post={{postSlug}}"
                            ),
                            bearer="accessToken",
                            tests=status_test(200),
                        ),
                        request_item(
                            "Approve comment",
                            "PATCH",
                            "/comments/{{commentId}}/",
                            bearer="accessToken",
                            body={
                                "is_approved": True,
                            },
                            tests=status_test(200),
                        ),
                    ],
                ),
                folder(
                    "09 - Contact and Dashboard",
                    [
                        request_item(
                            "Submit contact message",
                            "POST",
                            "/contact/",
                            body={
                                "name": "Postman Visitor",
                                "email": "visitor@example.com",
                                "subject": "Portfolio enquiry",
                                "message": (
                                    "I would like to discuss "
                                    "a potential project."
                                ),
                            },
                            tests=status_test(201) + [
                                "const data = pm.response.json();",
                                (
                                    "pm.collectionVariables.set("
                                    '"contactId", data.id);'
                                ),
                            ],
                        ),
                        request_item(
                            "List unread messages",
                            "GET",
                            "/contact/?is_read=false",
                            bearer="accessToken",
                            tests=status_test(200),
                        ),
                        request_item(
                            "Mark message as read",
                            "PATCH",
                            "/contact/{{contactId}}/",
                            bearer="accessToken",
                            body={
                                "is_read": True,
                            },
                            tests=status_test(200),
                        ),
                        request_item(
                            "Dashboard statistics",
                            "GET",
                            "/dashboard/stats/",
                            bearer="accessToken",
                            tests=status_test(200),
                        ),
                    ],
                ),
                folder(
                    "10 - Security Acceptance",
                    [
                        request_item(
                            "Registration must return 404",
                            "POST",
                            "/auth/register/",
                            body={},
                            tests=status_test(404),
                        ),
                        request_item(
                            "Anonymous post write returns 401",
                            "POST",
                            "/posts/",
                            body={
                                "title": "Hack attempt",
                            },
                            tests=status_test(401),
                        ),
                        request_item(
                            "Normal user write returns 403",
                            "POST",
                            "/skills/",
                            bearer="normalAccessToken",
                            body={
                                "name": "Unauthorized skill",
                                "category": "BACKEND",
                                "proficiency": 50,
                            },
                            description=(
                                "Populate normalAccessToken with a "
                                "token generated for a non-superuser."
                            ),
                            tests=status_test(403),
                        ),
                        request_item(
                            "Visitor draft detail returns 404",
                            "GET",
                            "/posts/{{draftSlug}}/",
                            description=(
                                "Set draftSlug to an existing draft."
                            ),
                            tests=status_test(404),
                        ),
                        request_item(
                            "Like without visitor ID returns 400",
                            "POST",
                            "/posts/{{postSlug}}/like/",
                            tests=status_test(400),
                        ),
                    ],
                ),
                folder(
                    "11 - Owner Session Actions",
                    [
                        request_item(
                            "Change password - run manually",
                            "POST",
                            "/auth/change-password/",
                            bearer="accessToken",
                            body={
                                "old_password": "{{password}}",
                                "new_password": "{{newPassword}}",
                            },
                            description=(
                                "Run manually. This changes the "
                                "configured owner password."
                            ),
                            tests=status_test(200),
                        ),
                        request_item(
                            "Logout - run last",
                            "POST",
                            "/auth/logout/",
                            bearer="accessToken",
                            body={
                                "refresh": "{{refreshToken}}",
                            },
                            tests=status_test(200),
                        ),
                    ],
                ),
            ],
        }

        # The visitor header is needed on post detail and like calls.
        for collection_folder in collection["item"]:
            for item in collection_folder["item"]:
                name = item["name"]

                if name in {
                    "Get post detail",
                    "Toggle post like",
                }:
                    item["request"]["header"].append(
                        {
                            "key": "X-Visitor-Id",
                            "value": "{{visitorId}}",
                            "type": "text",
                        }
                    )

        output_path = (
            Path(settings.BASE_DIR)
            / "postman_collection.json"
        )

        output_path.write_text(
            json.dumps(collection, indent=2),
            encoding="utf-8",
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {output_path}"
            )
        )