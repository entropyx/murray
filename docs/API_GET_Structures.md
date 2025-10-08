# API GET Request Structures

This document outlines the structure for the main GET requests to the Murray API.

## 1. Get Task Status and Results

This endpoint retrieves the status and results of a previously submitted analysis task.

**Endpoint:** `GET /task/{task_id}`

**Path Parameters:**

| Parameter | Type | Description |
| --- | --- | --- |
| `task_id` | String | **Required.** The ID of the task returned from a POST request to `/analyze/design` or `/analyze/evaluation`. |

**Example Request:**

```
GET /task/abc-123-def-456
Host: your-api-domain.com
X-API-Key: YOUR_API_KEY
```

**Possible Responses:**

The response is a JSON object that varies depending on the task's status.

*   **If the task is still running:**

    ```json
    {
      "task_id": "abc-123-def-456",
      "status": "STARTED",
      "results": {
        "message": "Task is currently running"
      }
    }
    ```

*   **If the task has completed successfully:**

    The `results` object will contain the full analysis output. The structure of the results will differ between `design` and `evaluation` tasks.

    ```json
    {
      "task_id": "abc-123-def-456",
      "status": "SUCCESS",
      "results": { 
        "...analysis_output..." 
      }
    }
    ```

*   **If the task has failed:**

    ```json
    {
      "task_id": "abc-123-def-456",
      "status": "FAILURE",
      "results": {
        "error": "Details about the error..."
      }
    }
    ```

*   **Other possible statuses:** `PENDING`, `RETRY`, `REVOKED`.

---

## 2. Root (Documentation Redirect)

Accessing the root of the API redirects to the interactive API documentation.

**Endpoint:** `GET /`

**Example Request:**

```
GET /
Host: your-api-domain.com
X-API-Key: YOUR_API_KEY
```

**Response:**

A `302 Found` redirect to the `/docs` page.
