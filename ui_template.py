HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">  <!-- Added for mobile -->
  <title>LSHA - Ltts Sales Helper Agent</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="icon" type="image/x-icon" href="/static/intelliswift_logo.png">
  <style>
    body { font-family: 'Poppins', sans-serif; }
    .chat-container { height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .dark .chat-container { background: #111827; }
    .chat-panel {
      display: flex;
      flex-direction: row;
      height: calc(100vh - 4rem);
      max-width: 1200px;
      margin: 2rem auto;
      background: white;
      border-radius: 2rem;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
      overflow: hidden;
      transition: background-color 0.3s ease, border-color 0.3s ease;
    }
    .dark .chat-panel { background: #1f2937; }

    .chat-box {
      flex: 4;
      display: flex;
      flex-direction: column;
      padding: 1.5rem;
    }

    .logo-panel {
      flex: 1;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 2rem;
      color: white;
      text-align: center;
      transition: background 0.3s ease;
    }

    .dark .logo-panel {
      background: linear-gradient(135deg, #3730a3 0%, #1e1b4b 100%);
    }

    .messages-area {
      flex-grow: 1;
      overflow-y: auto;
      padding-right: 1rem;
      scroll-behavior: smooth;
    }

    .message {
      display: flex;
      align-items: flex-end;
      margin-bottom: 1rem;
      animation: fadeIn 0.5s ease-in-out;
    }

    .message-content {
      max-width: 90%;
      padding: 0.75rem 1rem;
      border-radius: 1.25rem;
      position: relative;
      word-wrap: break-word;
    }

    .user-msg { flex-direction: row-reverse; }
    .user-msg .message-content {
      background-color: #7c3aed;
      color: white;
      border-bottom-right-radius: 0.25rem;
    }

    .bot-msg .message-content {
      background-color: #f1f5f9;
      color: #1e293b;
      border-bottom-left-radius: 0.25rem;
    }

    .dark .bot-msg .message-content {
      background-color: #374151;
      color: #e5e7eb;
    }

    .bot-msg .message-content a { color: #2563eb; }
    .dark .bot-msg .message-content a { color: #60a5fa; }
    .bot-msg .message-content h3, .bot-msg .message-content h4 { color: #4338ca; }
    .dark .bot-msg .message-content h3, .dark .bot-msg .message-content h4 { color: #a5b4fc; }

    .avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      color: white;
      flex-shrink: 0;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Responsive layout for mobile */
    @media (max-width: 768px) {
      .chat-panel {
        flex-direction: column-reverse;
        margin: 1rem;
        height: auto;
        border-radius: 1rem;
      }

      .chat-box {
        padding: 1rem;
      }

      .logo-panel {
        padding: 1rem;
      }

      .message-content {
        font-size: 0.9rem;
      }

      .messages-area {
        padding-right: 0;
      }
    }
  </style>
</head>
<body class="chat-container">
  <div class="chat-panel">
    <div class="chat-box">
      <div class="flex items-center justify-between text-2xl font-bold text-gray-800 dark:text-gray-200 mb-6 border-b pb-4 border-gray-200 dark:border-gray-700">
        <span class="italic text-red-800 dark:text-indigo-400 cursor-default">
          LSHA - Ltts Sales Helper Agent
        </span>
        <div class="flex items-center gap-4 relative">
          <button id="theme-toggle" type="button" title="Toggle theme" class="text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-700 rounded-lg text-sm p-2.5 transition-transform transform hover:scale-110">
            <svg id="theme-toggle-dark-icon" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path></svg>
            <svg id="theme-toggle-light-icon" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg"><path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 5.05A1 1 0 016.465 3.636l.707.707a1 1 0 01-1.414 1.414l-.707-.707a1 1 0 010-1.414zM5 11a1 1 0 100-2H4a1 1 0 100 2h1z" fill-rule="evenodd" clip-rule="evenodd"></path></svg>
          </button>
          <img src="/static/intelliswift_logo.png" alt="LSHA Logo" class="w-auto h-10">
          <form method="POST" action="/update_kb">
            <button type="submit" title="Update KB" class="text-gray-500 dark:text-gray-400 hover:text-purple-700 dark:hover:text-indigo-400 text-lg transition-transform transform hover:scale-125 focus:outline-none pr-2">
              🔄
            </button>
          </form>
        </div>
      </div>
      <div class="messages-area">
        {% for m in messages %}
          <div class="message {{ 'user-msg' if m['role'] == 'user' else 'bot-msg' }}">
            <div class="avatar {{ 'bg-purple-600' if m['role'] == 'user' else 'bg-gray-400' }}">
              {{ '👤' if m['role'] == 'user' else '🤖' }}
            </div>
            <div class="message-content">
              {{ m['content'] | safe }}
            </div>
          </div>
        {% endfor %}
      </div>
      <div id="spinner" class="text-sm text-purple-600 dark:text-purple-400 animate-pulse mt-4 hidden">
        ⏳ LSHA is thinking...
      </div>
      <form method="POST" id="chat-form" class="mt-auto flex gap-3 items-center pt-4" onsubmit="return handleFormSubmit(event)">
        <input name="q" id="chat-input" placeholder="Search or type 'yes'/'no'..."
               class="flex-grow rounded-full border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 shadow-sm px-6 py-3 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-all duration-300 dark:placeholder-slate-400" required autofocus>
        <button type="submit"
                class="bg-purple-600 hover:bg-purple-700 text-white font-semibold p-3 rounded-full shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-300">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
               class="feather feather-send"><line x1="22" y1="2" x2="11" y2="13"></line>
               <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </form>
    </div>
    <div class="logo-panel">
      <h2 class="italic text-3xl font-bold mb-2 transition-transform duration-300 ease-in-out hover:scale-105 cursor-default">LSHA</h2>
      <p class="text-lg text-purple-200 max-w-sm italic animate-pulse">
        Your AI-Powered Sales Helper Agent
      </p>
    </div>
  </div>
  <footer class="text-center text-xs text-slate-600 dark:text-slate-400 mt-6 mb-3">
    LSHA - Ltts Sales Helper Agent © 2025
  </footer>

  <script>
    const chatInput = document.getElementById('chat-input');
    const messagesArea = document.querySelector('.messages-area');
    const spinner = document.getElementById('spinner');
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
    const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');

    // Theme handling logic
    const applyTheme = (theme) => {
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
            themeToggleLightIcon.classList.remove('hidden');
            themeToggleDarkIcon.classList.add('hidden');
        } else {
            document.documentElement.classList.remove('dark');
            themeToggleDarkIcon.classList.remove('hidden');
            themeToggleLightIcon.classList.add('hidden');
        }
    };

    const currentTheme = localStorage.getItem('color-theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    applyTheme(currentTheme);

    themeToggleBtn.addEventListener('click', () => {
        const newTheme = document.documentElement.classList.contains('dark') ? 'light' : 'dark';
        localStorage.setItem('color-theme', newTheme);
        applyTheme(newTheme);
    });
    
    // Form submission logic
    function handleFormSubmit(event) {
      const userMessage = chatInput.value.trim();
      if (userMessage === '') return false;

      const messageDiv = document.createElement('div');
      messageDiv.className = 'message user-msg';
      const sanitizedMessage = userMessage.replace(/</g, "&lt;").replace(/>/g, "&gt;");
      messageDiv.innerHTML = `
        <div class="avatar bg-purple-600">👤</div>
        <div class="message-content">${sanitizedMessage}</div>
      `;
      messagesArea.appendChild(messageDiv);
      spinner.classList.remove("hidden");
      messagesArea.scrollTop = messagesArea.scrollHeight;

      setTimeout(() => { chatInput.value = ''; }, 50);
      return true;
    }

    // Onload logic
    window.addEventListener('load', () => {
      if (messagesArea) messagesArea.scrollTop = messagesArea.scrollHeight;
      if (chatInput) chatInput.focus();
    });
  </script>
</body>
</html>"""




# # ui_template.py
# HTML = """<!doctype html>
# <html lang="en">
# <head>
#   <meta charset="utf-8">
#   <title>LSHA - Ltts Sales Helper Agent</title>
#   <script src="https://cdn.tailwindcss.com"></script>
#   <link rel="preconnect" href="https://fonts.googleapis.com">
#   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
#   <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
#   <link rel="icon" type="image/x-icon" href="/static/intelliswift_logo.png">
#   <style>
#     body { font-family: 'Poppins', sans-serif; }
#     .chat-container { height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
#     .chat-panel { display: flex; height: calc(100vh - 4rem); max-width: 1200px; margin: 2rem auto; background: white; border-radius: 2rem; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); overflow: hidden; }
#     .chat-box { flex: 4; display: flex; flex-direction: column; padding: 1.5rem; }
#     .logo-panel { flex: 1; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem; color: white; text-align: center; }
#     .messages-area { flex-grow: 1; overflow-y: auto; padding-right: 1rem; scroll-behavior: smooth; }
#     .message { display: flex; align-items: flex-end; margin-bottom: 1rem; animation: fadeIn 0.5s ease-in-out; }
#     .message-content { max-width: 90%; padding: 0.75rem 1rem; border-radius: 1.25rem; position: relative; word-wrap: break-word; }
#     .user-msg { flex-direction: row-reverse; }
#     .user-msg .message-content { background-color: #7c3aed; color: white; border-bottom-right-radius: 0.25rem; }
#     .user-msg .avatar { margin-left: 0.75rem; }
#     .bot-msg .message-content { background-color: #f1f5f9; color: #1e293b; border-bottom-left-radius: 0.25rem; }
#     .bot-msg .message-content a { color: #2563eb; }
#     .bot-msg .message-content h3, .bot-msg .message-content h4 { color: #4338ca; }
#     .avatar { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; color: white; flex-shrink: 0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
#     @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
#   </style>
# </head>
# <body class="chat-container">
#   <div class="chat-panel">
#     <!-- Chat Side -->
#     <div class="chat-box">
#       <div class="flex items-center justify-between text-2xl font-bold text-gray-800 mb-6 border-b pb-4">
#         <span class="italic text-red-800 cursor-default">
#           LSHA - Ltts Sales Helper Agent
#         </span>
#         <div class="flex items-center gap-2 relative">
#           <img src="/static/intelliswift_logo.png" alt="LSHA Logo" class="w-auto h-10 mr-2">
#           <form method="POST" action="/update_kb">
#             <button type="submit" title="Update KB:" class="text-gray-600 hover:text-purple-700 text-lg transition-transform transform hover:scale-125 focus:outline-none">
#               🔄
#             </button>
#           </form>
#         </div>
#       </div>
#       <div class="messages-area">
#         {% for m in messages %}
#           <div class="message {{ 'user-msg' if m['role'] == 'user' else 'bot-msg' }}">
#             <div class="avatar {{ 'bg-purple-600' if m['role'] == 'user' else 'bg-gray-400' }}">
#               {{ '👤' if m['role'] == 'user' else '🤖' }}
#             </div>
#             <div class="message-content">
#               {{ m['content'] | safe }}
#             </div>
#           </div>
#         {% endfor %}
#       </div>
#       <div id="spinner" class="text-sm text-purple-600 animate-pulse mt-4 hidden">
#         ⏳ LSHA is thinking...
#       </div>
#       <form method="POST" id="chat-form" class="mt-auto flex gap-3 items-center pt-4" onsubmit="return handleFormSubmit(event)">
#         <input name="q" id="chat-input" placeholder="Search or type 'yes'/'no'..."
#                class="flex-grow rounded-full border border-slate-300 shadow-sm px-6 py-3 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-all duration-300" required autofocus>
#         <button type="submit"
#                 class="bg-purple-600 hover:bg-purple-700 text-white font-semibold p-3 rounded-full shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-300">
#           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
#                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
#                class="feather feather-send"><line x1="22" y1="2" x2="11" y2="13"></line>
#                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
#           </svg>
#         </button>
#       </form>
#     </div>
#     <!-- Logo Panel -->
#     <div class="logo-panel">
#       <h2 class="italic text-3xl font-bold mb-2 transition-transform duration-300 ease-in-out hover:scale-105 cursor-default">LSHA</h2>
#       <p class="text-lg text-purple-200 max-w-sm italic animate-pulse">
#         Your AI-Powered Sales Helper Agent
#       </p>
#     </div>
#   </div>
#   <footer class="text-center text-xs text-slate-600 mt-6 mb-3">
#     LSHA - Ltts Sales Helper Agent © 2025
#   </footer>

#   <script>
#     const chatInput = document.getElementById('chat-input');
#     const messagesArea = document.querySelector('.messages-area');
#     const spinner = document.getElementById('spinner');

#     function handleFormSubmit(event) {
#       const userMessage = chatInput.value.trim();
#       if (userMessage === '') return false;

#       const messageDiv = document.createElement('div');
#       messageDiv.className = 'message user-msg';
#       const sanitizedMessage = userMessage.replace(/</g, "&lt;").replace(/>/g, "&gt;");
#       messageDiv.innerHTML = `
#         <div class="avatar bg-purple-600">👤</div>
#         <div class="message-content">${sanitizedMessage}</div>
#       `;
#       messagesArea.appendChild(messageDiv);
#       spinner.classList.remove("hidden");
#       messagesArea.scrollTop = messagesArea.scrollHeight;

#       setTimeout(() => { chatInput.value = ''; }, 50);
#       return true;
#     }

#     window.addEventListener('load', () => {
#       if (messagesArea) messagesArea.scrollTop = messagesArea.scrollHeight;
#       if (chatInput) chatInput.focus();
#     });
#   </script>
# </body>
# </html>"""




# # ui_template.py
# HTML = """<!doctype html>
# <html lang="en">
# <head>
#   <meta charset="utf-8">
#   <title>LSHA - Ltts Sales Helper Agent</title>
#   <script src="https://cdn.tailwindcss.com"></script>
#   <link rel="preconnect" href="https://fonts.googleapis.com">
#   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
#   <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
#   <link rel="icon" type="image/x-icon" href="/static/intelliswift_logo.png">
#   <style>
#     body { font-family: 'Poppins', sans-serif; }
#     .chat-container { height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
#     .chat-panel { display: flex; height: calc(100vh - 4rem); max-width: 1200px; margin: 2rem auto; background: white; border-radius: 2rem; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); overflow: hidden; }
#     .chat-box { flex: 4; display: flex; flex-direction: column; padding: 1.5rem; }
#     .logo-panel { flex: 1; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem; color: white; text-align: center; }
#     .messages-area { flex-grow: 1; overflow-y: auto; padding-right: 1rem; scroll-behavior: smooth; }
#     .message { display: flex; align-items: flex-end; margin-bottom: 1rem; animation: fadeIn 0.5s ease-in-out; }
#     .message-content { max-width: 90%; padding: 0.75rem 1rem; border-radius: 1.25rem; position: relative; word-wrap: break-word; }
#     .user-msg { flex-direction: row-reverse; }
#     .user-msg .message-content { background-color: #7c3aed; color: white; border-bottom-right-radius: 0.25rem; }
#     .user-msg .avatar { margin-left: 0.75rem; }
#     .bot-msg .message-content { background-color: #f1f5f9; color: #1e293b; border-bottom-left-radius: 0.25rem; }
#     .bot-msg .message-content a { color: #2563eb; }
#     .bot-msg .message-content h3, .bot-msg .message-content h4 { color: #4338ca; }
#     .avatar { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; color: white; flex-shrink: 0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
#     @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
#   </style>
# </head>
# <body class="chat-container">
#   <div class="chat-panel">
#     <!-- Chat Side -->
#     <div class="chat-box">
#       <div class="flex items-center justify-between text-2xl font-bold text-gray-800 mb-6 border-b pb-4">
#         <span class="italic transition-transform duration-300 text-red-800 ease-in-out hover:scale-105 cursor-default">
#           LSHA - Ltts Sales Helper Agent
#         </span>
#         <div class="flex items-center gap-2 relative">
#           <img src="/static/intelliswift_logo.png" alt="LSHA Logo" class="w-auto h-10">
#           <form method="POST" action="/update_kb">
#             <button type="submit" title="Update KB:" class="text-gray-600 hover:text-purple-700 text-lg transition-transform transform hover:scale-125 focus:outline-none">
#               🔄
#             </button>
#           </form>
#         </div>
#       </div>
#       <div class="messages-area">
#         {% for m in messages %}
#           <div class="message {{ 'user-msg' if m['role'] == 'user' else 'bot-msg' }}">
#             <div class="avatar {{ 'bg-purple-600' if m['role'] == 'user' else 'bg-gray-400' }}">
#               {{ '👤' if m['role'] == 'user' else '🤖' }}
#             </div>
#             <div class="message-content">
#               {{ m['content'] | safe }}
#             </div>
#           </div>
#         {% endfor %}
#       </div>
#       <div id="spinner" class="text-sm text-purple-600 animate-pulse mt-4 hidden">
#         ⏳ LSHA is thinking...
#       </div>
#       <form method="POST" id="chat-form" class="mt-auto flex gap-3 items-center pt-4" onsubmit="return handleFormSubmit(event)">
#         <input name="q" id="chat-input" placeholder="Search or type 'yes'/'no'..."
#                class="flex-grow rounded-full border border-slate-300 shadow-sm px-6 py-3 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-all duration-300" required autofocus>
#         <button type="submit"
#                 class="bg-purple-600 hover:bg-purple-700 text-white font-semibold p-3 rounded-full shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-300">
#           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
#                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
#                class="feather feather-send"><line x1="22" y1="2" x2="11" y2="13"></line>
#                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
#           </svg>
#         </button>
#       </form>
#     </div>
#     <!-- Logo Panel -->
#     <div class="logo-panel">
#       <h2 class="italic text-3xl font-bold mb-2 transition-transform duration-300 ease-in-out hover:scale-105 cursor-default">LSHA</h2>
#       <p class="text-lg text-purple-200 max-w-sm italic animate-pulse">
#         Your AI-Powered Sales Helper Agent
#       </p>
#     </div>
#   </div>
#   <footer class="text-center text-xs text-slate-600 mt-6 mb-3">
#     LSHA - Ltts Sales Helper Agent © 2025
#   </footer>

#   <script>
#     const chatInput = document.getElementById('chat-input');
#     const messagesArea = document.querySelector('.messages-area');
#     const spinner = document.getElementById('spinner');

#     function handleFormSubmit(event) {
#       const userMessage = chatInput.value.trim();

#       if (userMessage === '') {
#         return false;
#       }

#       // Show user message immediately
#       const messageDiv = document.createElement('div');
#       messageDiv.className = 'message user-msg';
#       const sanitizedMessage = userMessage.replace(/</g, "&lt;").replace(/>/g, "&gt;");
#       messageDiv.innerHTML = `
#           <div class="avatar bg-purple-600">👤</div>
#           <div class="message-content">${sanitizedMessage}</div>
#       `;
#       messagesArea.appendChild(messageDiv);
#       spinner.classList.remove("hidden");
#       messagesArea.scrollTop = messagesArea.scrollHeight;

#       // Clear input after short delay to allow POST to send value
#       setTimeout(() => {
#         chatInput.value = '';
#       }, 50);

#       return true; // Let the form submit
#     }

#     window.addEventListener('load', () => {
#       if (messagesArea) {
#         messagesArea.scrollTop = messagesArea.scrollHeight;
#       }
#       if (chatInput) {
#         chatInput.focus();
#       }
#     });
#   </script>
# </body>
# </html>"""
