#!/usr/bin/env python3
"""
PhD Finder Backend Server
- Serves static files (index.html, medical-bioinformatics.html, evaluate.html)
- Proxies DeepSeek API calls (/api/evaluate) to bypass CORS
- Keeps API key server-side only
"""
import http.server
import json
import urllib.request
import urllib.error
import os
import sys
from pathlib import Path

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    # Fallback: read from .env file
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                DEEPSEEK_API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
if not DEEPSEEK_API_KEY:
    print("ERROR: DEEPSEEK_API_KEY not set. Create .env file or set environment variable.")
    sys.exit(1)
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
PORT = 8888
ROOT_DIR = Path(__file__).parent

class PhDHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def do_POST(self):
        if self.path == "/api/evaluate":
            self.handle_evaluate()
        else:
            self.send_error(404)

    def handle_evaluate(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)

            background = data.get("background", "").strip()
            target_region = data.get("target_region", "all")
            target_direction = data.get("target_direction", "both")

            if not background:
                self.send_json({"error": "请填写背景信息"})
                return

            prompt = self.build_prompt(background, target_region, target_direction)

            deepseek_response = self.call_deepseek(prompt)

            self.send_json({"result": deepseek_response})

        except Exception as e:
            self.send_json({"error": f"服务器错误: {str(e)}"})

    def build_prompt(self, background, target_region, target_direction):
        region_desc = {
            "all": "NTU新加坡、澳大利亚（Go8及主要研究所）、新西兰（Auckland/Otago/Massey等）",
            "NTU": "NTU新加坡（Nanyang Technological University）",
            "Australia": "澳大利亚（UQ, UNSW, UniMelb, Monash, QUT, RMIT, UOW, Adelaide + Garvan/WEHI/Baker研究所）",
            "New Zealand": "新西兰（University of Auckland, University of Otago, Massey University, Malaghan Institute）"
        }
        dir_desc = {
            "both": "环境微生物/水处理 和 药学/医学生信",
            "environmental": "环境微生物学 & 水处理工程（含宏基因组/AMR/生信）",
            "medical": "药学 & 医学生信（单细胞组学/癌症基因组学/药物发现/组织器官疾病）"
        }

        region_text = region_desc.get(target_region, region_desc["all"])
        dir_text = dir_desc.get(target_direction, dir_desc["both"])

        return f"""你是一位资深 PhD 申请顾问，专门帮助国际学生评估申请 NTU 新加坡、澳大利亚和新西兰的博士项目录取概率。

## 申请者背景
{background}

## 目标地区和方向
- 目标地区：{region_text}
- 目标方向：{dir_text}

## 已知录取参考信息

### NTU 新加坡
- 综合录取率约 25-30%（全校），工程/理学院国际生 PhD 竞争激烈
- Research Scholarship 月薪 S$2,200-2,700（通过 PhD Qualifying Exam 后涨至 S$2,700-3,200）
- 典型录取画像：985/211 本科 GPA 3.5/4.0 (85/100) 以上 + 相关科研经历；双非需突出论文发表
- 1 月 / 8 月两季入学；新加坡政府偏好招中国学生（文化相近但名额有限）
- LKCMedicine/SBS/SCELSE 各自独立招生，建议直接联系导师

### 澳大利亚
- Group of Eight (Go8) 大学国际生 PhD 录取率约 30-40%，但全奖 (RTP) 竞争极激烈（约 15-20% 成功率）
- RTP 全奖：A$37,000/年 生活费 + 免学费；大学内部奖学金 (UIPA 等) 金额相似
- 典型全奖画像：本科+硕士 GPA 85+/100（约等于澳洲 First Class Honours 80%+）+ 有发表记录
- UNSW/EMBL Australia 奖学金可达 A$50,000/年
- 8-10 月主轮截止（次年 2-3 月入学）；部分导师有自有经费可绕过 GPA 排名
- 医学研究所 (WEHI/Garvan/Baker) 录取标准更高但奖学金更丰厚
- 签证新规 GS (Genuine Student) 需展示清晰回国计划

### 新西兰
- 整体 PhD 录取率较高（约 35-50%），但全奖名额少（UoA Doctoral Scholarship 约 10-15% 成功率）
- UoA Doctoral Scholarship: NZ$33,000/年 + 免学费；GPA 门槛 7.0/9.0 (≈85/100)
- 导师经费 (Marsden/HRC) 可绕过 GPA 排名直接录取
- 对中国学生签证友好、审批快；CSC 联合培养较受欢迎
- 全年可入学但奖学金有轮次截止

### 关键加分项（跨地区通用）
- 已发表 SCI/SSCI 论文（一作 >>> 共同作者）
- 导师课题经费支持（arguably 最重要因素——有钱的导师说了算）
- GitHub 有完整生信 pipeline（对生信方向）
- 明确的 Research Proposal 匹配导师方向
- 海外暑研/交换经历
- 推荐信来自目标导师认识的人

## 评估要求

请按以下格式输出评估报告（用中文）：

### 一、整体竞争力评分（满分 100）
- 给出分数并简要说明

### 二、各地区录取概率估算
- **NTU 新加坡**: [百分比] - [分析]
- **澳大利亚**: [百分比] - [分析]
- **新西兰**: [百分比] - [分析]

### 三、优势与短板
- ✅ 优势（2-4 点）
- ⚠️ 短板（2-4 点）

### 四、提升建议（具体可操作）
1. [建议 1]
2. [建议 2]
3. [建议 3]

### 五、推荐申请的 Top 5 导师/项目
按匹配度排序，说明为什么适合

### 六、时间线建议
建议什么时候开始套磁、准备材料、提交申请

请保持客观、量化的评估风格。如果背景信息不完整，基于已有信息给出最佳估计。"""

    def call_deepseek(self, prompt):
        payload = json.dumps({
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
            "stream": False
        }).encode("utf-8")

        req = urllib.request.Request(
            DEEPSEEK_API_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else str(e)
            return f"DeepSeek API 错误 (HTTP {e.code}): {error_body}"
        except Exception as e:
            return f"请求失败: {str(e)}"

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        # Silence default logging; uncomment to debug
        sys.stderr.write(f"[server] {args[0]}\n")


if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════╗
║     🧬 PhD Finder Server                     ║
║     http://localhost:{PORT}                    ║
║                                              ║
║  Pages:                                      ║
║  /index.html         环境微生物/水处理        ║
║  /medical-bioinfo..  药学/医学生信            ║
║  /evaluate.html      🤖 AI 录取评估        ║
║                                              ║
║  API: POST /api/evaluate                     ║
╚══════════════════════════════════════════════╝
""")
    server = http.server.HTTPServer(("0.0.0.0", PORT), PhDHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
