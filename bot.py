import discord
from discord.ext import commands
import random
import string
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import requests

# Initialize the bot
intents = discord.Intents.default()
intents.message_content = True  # Enable access to message content
bot = commands.Bot(command_prefix="/", intents=intents)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Store active codes (user_id: {"code": code, "verified": False})
active_codes = {}

# Webhook URL for logging
WEBHOOK_URL = "YOUR_WEBHOOK_URL"  # Replace with your Discord webhook URL

# Function to generate a random code
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def verify(ctx):
    user_id = ctx.author.id

    # Check if the user already has an active code
    if user_id in active_codes and not active_codes[user_id]["verified"]:
        await ctx.send("You already have an active verification code. Check your DMs.", delete_after=5)
        return

    # Generate a new code
    code = generate_code()

    # Store the code for this user
    active_codes[user_id] = {"code": code, "verified": False}

    # Send the code to the user privately
    try:
        await ctx.author.send(
            f"Your verification code is: `{code}`.\n"
            f"Please go to https://discord-verify.vercel.app and enter this code to complete verification."
        )
        await ctx.send("Check your DMs for your verification code.", delete_after=5)
    except discord.Forbidden:
        await ctx.send("I couldn't send you a DM. Please enable DMs from server members and try again.")

@bot.command()
async def check_verification(ctx):
    user_id = ctx.author.id

    # Check if the user has an active code
    if user_id not in active_codes:
        await ctx.send("You don't have an active verification code. Use `/verify` to get one.", delete_after=5)
        return

    # Check if the user is verified
    if active_codes[user_id]["verified"]:
        # Assign the "Verified" role
        role = discord.utils.get(ctx.guild.roles, name="Verified")
        if role:
            await ctx.author.add_roles(role)
            await ctx.send("You have been verified!", delete_after=5)
        else:
            await ctx.send("The 'Verified' role does not exist. Please contact an admin.", delete_after=5)
    else:
        await ctx.send("You haven't completed the verification process on the site yet.", delete_after=5)

# Flask route to log IP and verify codes
@app.route("/verify_code/<code>", methods=["POST"])
def verify_code(code):
    # Get the user's IP address
    ip_address = request.remote_addr

    # Log that the user has entered the site
    webhook_data = {
        "content": f"User has entered the site (IP: {ip_address}) - Awaiting code."
    }
    requests.post(WEBHOOK_URL, json=webhook_data)

    # Find the user with this code
    for user_id, data in active_codes.items():
        if data["code"] == code and not data["verified"]:
            # Mark the code as verified
            active_codes[user_id]["verified"] = True

            # Log successful verification
            webhook_data = {
                "content": f"User <@{user_id}> verified successfully (IP: {ip_address})."
            }
            requests.post(WEBHOOK_URL, json=webhook_data)

            return jsonify({"success": True, "message": "Code verified successfully."}), 200

    return jsonify({"success": False, "message": "Invalid or already verified code."}), 400

# Run the bot and Flask app
if __name__ == "__main__":
    # Run the Flask app in a separate thread
    flask_thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000))
    flask_thread.daemon = True
    flask_thread.start()

    # Run the Discord bot
    bot.run('MTMzMTE0MjYwMzI4MjA1NTE3OA.GJnBA8.9WbBzgUNQM6OVMUVnEKt3EM6pnLAz4fkDZ4vYA')  # Replace with your actual bot token
