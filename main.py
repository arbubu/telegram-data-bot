import os
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# .env ဖိုင်အစား Environment Variables ကနေ တိုက်ရိုက် load လုပ်မှာဖြစ်ပါတယ်
load_dotenv() 
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini API Key ကို သတ်မှတ်ခြင်း
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("Gemini Model configured successfully.")
except Exception as e:
    print(f"Error configuring Gemini: {e}")
    model = None

# /start command အတွက် function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('မင်္ဂလာပါ! ကျေးဇူးပြု၍ ခွဲခြမ်းစိတ်ဖြာလိုသော အရောင်းဒေတာ Excel ဖိုင်ကို ပေးပို့ပါ။')

# Gemini ကနေ သုံးသပ်ချက်တောင်းမယ့် function
def get_ai_analysis(summary: str) -> str:
    if not model:
        return "Gemini AI ကို ပြင်ဆင်ရာမှာ အမှားအယွင်း ရှိနေပါတယ်။ ကျေးဇူးပြု၍ API Key ကို စစ်ဆေးပါ။"

    prompt = f"""
    အောက်မှာ ကျွန်တော့်ရဲ့ အရောင်းဒေတာ အနှစ်ချုပ်ဖြစ်ပါတယ်။

    Data Summary:
    {summary}

    ဒီအချက်အလက်တွေပေါ်မူတည်ပြီး လူတစ်ယောက်အနေနဲ့ လုပ်ငန်းသုံးသပ်ချက် (Business Analysis) တစ်ခုကို ပြုလုပ်ပေးပါ။ အဓိက လမ်းကြောင်း (trends) တွေ၊ အားသာချက်၊ အားနည်းချက်တွေနဲ့ ရှေ့ဆက်လုပ်ဆောင်သင့်တဲ့ အကြံပြုချက်တွေကို အသေးစိတ်ရှင်းပြပေးပါ။
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI သုံးသပ်ချက်ရယူရာမှာ အမှားအယွင်းဖြစ်သွားပါတယ်: {e}"

# Document ဖိုင်ကို လက်ခံပြီး ခွဲခြမ်းစိတ်ဖြာမယ့် function
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document
    file = await context.bot.get_file(document.file_id)
    # ဖိုင်အမည်ကို .xlsx ဖြင့်အဆုံးသတ်စေရန်
    file_path = f"downloaded_{document.file_id}.xlsx"
    await file.download_to_drive(file_path)

    await update.message.reply_text(f"'{document.file_name}' ဖိုင်ကို လက်ခံရရှိပြီး ခွဲခြမ်းစိတ်ဖြာနေပါပြီ... AI သုံးသပ်ချက်ကိုပါ တစ်ခါတည်း ပြုလုပ်နေပါတယ်၊ ခဏစောင့်ပေးပါ...")

    try:
        # === ဒီနေရာက အဓိက ပြင်ဆင်မှုပါ ===
        # Pandas ကိုသုံးပြီး Excel ဖိုင်ကို ဖတ်ခြင်း
        df = pd.read_excel(file_path)

        # Data ရဲ့ အခြေခံ စာရင်းအင်းအချက်အလက် (Descriptive Statistics) တွေကို တွက်ချက်ခြင်း
        # ဂဏန်းပါသော columns များကိုသာ ရွေးပြီး describe လုပ်ပါမည်။
        numeric_df = df.select_dtypes(include='number')
        analysis_summary = numeric_df.describe().to_string()

        # သင့် Excel file column name များနှင့် ကိုက်ညီအောင် ပြင်ဆင်ရန် လိုအပ်နိုင်သည်
        # ဥပမာ - 'Revenue' နှင့် 'Units_Sold' columns များရှိသည်ဟု ယူဆထားသည်
        total_revenue = numeric_df['Revenue'].sum() if 'Revenue' in numeric_df else 'N/A'
        total_units_sold = numeric_df['Units_Sold'].sum() if 'Units_Sold' in numeric_df else 'N/A'

        summary_report = f"""
      # အနှစ်ချုပ်ကို Gemini ဆီပို့ပြီး သုံးသပ်ချက်တောင်းခြင်း
ai_final_report = get_ai_analysis(summary_report)
        await update.message.reply_text(ai_final_report)

    except Exception as e:
        await update.message.reply_text(f"ဖိုင်ကို ခွဲခြမ်းစိတ်ဖြာရာမှာ အမှားအယွင်းဖြစ်သွားပါတယ်: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def main() -> None:
    print("Data Analysis Bot is starting...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    # === Excel ဖိုင်အမျိုးအစားများကို လက်ခံရန် Filter ကို ပြင်ဆင်ခြင်း ===
    excel_mimetypes = [
        'application/vnd.ms-excel', 
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ]
    application.add_handler(MessageHandler(filters.Document.MimeType(excel_mimetypes), handle_document))
    
    print("Bot is polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
