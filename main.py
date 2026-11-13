
from flask import Flask, request, render_template_string
import math

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Polash Pro Trading Bot</title>
<style>
body {
 background:#080d18; color:white; font-family:Arial;
 padding:18px; margin:0;
}
.container {
 max-width:600px; margin:auto;
}
h1 {color:#00e5a0;text-align:center;}
.sub {text-align:center;color:#aaa;}
.card {
 background:#141e30; padding:18px;
 border-radius:14px; margin:16px 0;
 border:1px solid #26354c;
}
select,textarea,button {
 width:100%; padding:13px; margin-top:10px;
 border-radius:9px; border:1px solid #40516b;
 background:#0b1424; color:white; font-size:16px;
 box-sizing:border-box;
}
textarea {height:120px;}
button {
 background:#00c990; color:#00150e;
 font-weight:bold; border:0;
}
.signal {
 text-align:center; font-size:30px;
 font-weight:bold; color:#00e5a0;
}
small {color:#aaa;}
</style>
</head>
<body>
<div class="container">
<h1>POLASH PRO</h1>
<p class="sub">OTC TRADING SIGNAL ANALYSIS</p>

<div class="card">
<h3>Market: Pocket Option OTC</h3>
<label>Select Expiry Time</label>
<form method="POST">
<select name="expiry">
{% for t in ["5 Seconds","15 Seconds","30 Seconds","1 Minute"] %}
<option value="{{t}}" {% if expiry==t %}selected{% endif %}>{{t}}</option>
{% endfor %}
</select>
<h3>Enter candle closing prices</h3>
<textarea name="prices" placeholder="Example: 1.2345, 1.2348, 1.2350 ...">{{prices}}</textarea>
<small>কমপক্ষে 35টি সাম্প্রতিক closing price কমা দিয়ে লিখুন।</small>
<button type="submit">ANALYZE MARKET</button>
</form>
</div>

{% if result %}
<div class="card">
<h3>Analysis Result</h3>
<div class="signal">{{result.signal}}</div>
<p>Expiry: {{expiry}}</p>
<p>RSI: {{result.rsi}}</p>
<p>MACD: {{result.macd}}</p>
<p>Bollinger: {{result.bb}}</p>
<p>Support: {{result.support}}</p>
<p>Resistance: {{result.resistance}}</p>
<p>Indicator agreement: {{result.score}} / 4</p>
<p>{{result.message}}</p>
</div>
{% endif %}

<div class="card">
<h3>Indicators</h3>
<p>✓ RSI Analysis</p>
<p>✓ MACD Trend</p>
<p>✓ Bollinger Bands</p>
<p>✓ Support & Resistance</p>
</div>
<p class="sub">Educational analysis only. No guaranteed profits.</p>
</div>
</body>
</html>
"""

def ema(values, period):
    result = []
    k = 2 / (period + 1)
    current = sum(values[:period]) / period
    result.append(current)
    for value in values[period:]:
        current = value * k + current * (1-k)
        result.append(current)
    return result

def analyze(prices):
    if len(prices) < 35:
        raise ValueError("কমপক্ষে 35টি closing price দিন।")

    gains, losses = [], []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14

    if avg_loss == 0:
        rsi = 100 if avg_gain else 50
    else:
        rsi = 100 - (100 / (1 + avg_gain / avg_loss))

    fast = ema(prices, 12)
    slow = ema(prices, 26)
    macd_values = [
        fast[i + len(fast)-len(slow)] - slow[i]
        for i in range(len(slow))
    ]
    signal_values = ema(macd_values, 9)

    macd = macd_values[-1]
    macd_signal = signal_values[-1]

    recent = prices[-20:]
    middle = sum(recent) / 20
    variance = sum((x-middle)**2 for x in recent) / 20
    deviation = math.sqrt(variance)
    upper = middle + 2 * deviation
    lower = middle - 2 * deviation

    support = min(recent)
    resistance = max(recent)
    price = prices[-1]

    score = 0
    if rsi < 35:
        score += 1
    elif rsi > 65:
        score -= 1

    if macd > macd_signal:
        score += 1
    elif macd < macd_signal:
        score -= 1

    if price > middle:
        score += 1
    elif price < middle:
        score -= 1

    if price <= lower:
        score += 1
    elif price >= upper:
        score -= 1

    if score >= 2:
        signal = "CALL"
        message = "Bullish indicator agreement. Confirm with live chart."
    elif score <= -2:
        signal = "PUT"
        message = "Bearish indicator agreement. Confirm with live chart."
    else:
        signal = "WAIT"
        message = "Clear agreement নেই। অপেক্ষা করুন।"

    return {
        "signal": signal,
        "rsi": round(rsi, 2),
        "macd": round(macd, 7),
        "bb": f"{round(lower, 6)} - {round(upper, 6)}",
        "support": round(support, 6),
        "resistance": round(resistance, 6),
        "score": abs(score),
        "message": message
    }

@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    prices_text = ""
    expiry = "15 Seconds"

    if request.method == "POST":
        prices_text = request.form.get("prices", "")
        expiry = request.form.get("expiry", "15 Seconds")

        try:
            prices = [
                float(x.strip())
                for x in prices_text.split(",")
                if x.strip()
            ]
            if not all(math.isfinite(x) and x > 0 for x in prices):
                raise ValueError("সঠিক positive price দিন।")
            result = analyze(prices)
        except ValueError as e:
            result = {
                "signal": "ERROR",
                "rsi": "-",
                "macd": "-",
                "bb": "-",
                "support": "-",
                "resistance": "-",
                "score": "-",
                "message": str(e)
            }

    return render_template_string(
        HTML, result=result, prices=prices_text, expiry=expiry
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
