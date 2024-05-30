import stardog

db = "DataPlatformDesign"
conn_details = {
    "endpoint": "https://sd-1ee4a6e0.stardog.cloud:5820",
    "username": "mpasini",
    "password": "mpasinimpasini",
}

with stardog.Connection(db, **conn_details) as conn:
    results = conn.select("select * {?s ?p ?o}", reasoning=True)

    print(results)
    print("Done")
