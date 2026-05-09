{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Start MTN Payment</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #FFFFFF; /* Clean White */
            color: #2E2E2E; /* Charcoal Black */
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 500px;
            margin: 80px auto;
            padding: 30px;
            border-radius: 12px;
            background-color: #8BC0A9; /* Soft Mint Green */
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        h2 {
            text-align: center;
            color: #D71920; /* Fire Red */
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #2E2E2E; /* Charcoal Black */
        }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            margin-bottom: 20px;
            border-radius: 6px;
            border: 1px solid #A7D8DE; /* Light Caring Blue */
        }
        button {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            background-color: #D71920; /* Fire Red */
            color: #FFFFFF; /* Clean White */
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s ease;
        }
        button:hover {
            background-color: #FDBB30; /* Safety Gold */
        }
        .note {
            margin-top: 15px;
            text-align: center;
            color: #A7D8DE; /* Light Caring Blue */
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Pay with MTN MoMo</h2>
        <form method="post">
            {% csrf_token %}
            <label for="phone_number">Phone Number:</label>
            <input type="text" name="phone_number" id="phone_number" placeholder="e.g., 024XXXXXXXX" required>
            <button type="submit">Pay Now</button>
        </form>
        <p class="note">All payments are processed via sandbox for testing</p>
    </div>
</body>
</html>
