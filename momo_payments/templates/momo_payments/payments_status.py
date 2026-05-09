{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Payment Status</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #FFFFFF; /* Clean White */
            color: #2E2E2E; /* Charcoal Black */
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 600px;
            margin: 60px auto;
            padding: 30px;
            border-radius: 12px;
            background-color: #8BC0A9; /* Soft Mint Green */
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        h2 {
            text-align: center;
            color: #D71920; /* Fire Red */
        }
        .status {
            font-size: 18px;
            margin: 20px 0;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            color: #FFFFFF;
        }
        .SUCCESS {
            background-color: #8BC0A9; /* Soft Mint Green */
        }
        .FAILED {
            background-color: #D71920; /* Fire Red */
        }
        .PENDING {
            background-color: #FDBB30; /* Safety Gold */
            color: #2E2E2E; /* Charcoal Black */
        }
        pre {
            background-color: #A7D8DE; /* Light Caring Blue */
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
        }
        a.button {
            display: block;
            text-align: center;
            margin-top: 20px;
            padding: 12px;
            background-color: #D71920; /* Fire Red */
            color: #FFFFFF;
            text-decoration: none;
            border-radius: 8px;
            font-size: 16px;
        }
        a.button:hover {
            background-color: #FDBB30; /* Safety Gold */
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Payment Status</h2>
        <p><strong>Reference:</strong> <span id="payment-ref">{{ payment.reference }}</span></p>
        <div class="status {{ payment.status }}" id="payment-status">
            Status: {{ payment.status }}
        </div>
        <h3>Raw Response:</h3>
        <pre id="raw-response">{{ status_data|safe }}</pre>

        <a class="button" href="{% url 'momo_pay:start_mtn_payment' payment.id_request.id %}">Pay Again</a>
    </div>

    <script>
        const reference = "{{ payment.reference }}";
        const statusDiv = document.getElementById("payment-status");
        const rawDiv = document.getElementById("raw-response");

        // Polling every 5 seconds
        const interval = setInterval(() => {
            fetch(`/payments/mtn/status/${reference}/?json=1`)
                .then(response => response.json())
                .then(data => {
                    statusDiv.textContent = "Status: " + data.status;
                    statusDiv.className = "status " + data.status;
                    rawDiv.textContent = JSON.stringify(data.raw_response, null, 2);

                    // Stop polling if SUCCESS or FAILED
                    if (data.status === "SUCCESS" || data.status === "FAILED") {
                        clearInterval(interval);
                    }
                })
                .catch(err => console.error("Polling error:", err));
        }, 5000);
    </script>
</body>
</html>
