from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.post(
    "/api/v1/transparencia/jobs/beneficios/seed",
    json={
        "resource": "novo-bolsa-familia-por-municipio",
        "mesAnoInicio": "202303",
        "mesAnoFim": "202304",
        "jobGranularity": "municipio_mes"
    }
)
print("Status Code:", response.status_code)
print("Response JSON:")
print(response.json())

# And what if state is not provided at all and body is empty?
# Wait, if body is empty it gives 422 because resource is required? Let's check!
response_empty = client.post("/api/v1/transparencia/jobs/beneficios/seed")
print("Status Code Empty:", response_empty.status_code)
print("Empty JSON:")
print(response_empty.json())

