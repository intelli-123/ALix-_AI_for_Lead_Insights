HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ALix - AI for Lead Insights</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="icon" href="/static/alix_logo.png">
</head>
<body class="bg-gradient-to-br from-sky-100 to-indigo-200 min-h-screen p-8 font-sans">
  <div class="max-w-4xl mx-auto bg-white shadow-xl rounded-lg p-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-3xl font-bold text-indigo-700 flex items-center gap-3">
        <img src="/static/alix_logo.png" class="w-10 h-10"> ALix - AI for Lead Insights
      </h1>
    </div>

    <form method="POST" class="flex gap-3 mb-6" onsubmit="showLoading()">
      <input name="q" value="{{ q }}" placeholder="Enter person or company name"
             class="flex-auto rounded-md border border-slate-300 shadow-sm px-4 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" required>
      <button type="submit"
              class="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-6 py-2 rounded-md shadow-md transition">
        Search
      </button>
    </form>

    <div id="spinner" class="text-center text-indigo-600 font-medium animate-pulse my-4 hidden">
      🔍 Fetching results... please wait.
    </div>

    {% if hits is not none %}
      {% if hits %}
        <div class="border border-slate-200 bg-indigo-50 p-5 rounded-md shadow-sm space-y-2">
          <p><strong class="text-slate-700">Name:</strong> {{ hits[0].designation or '—' }}</p>
          <p><strong class="text-slate-700">Link:</strong> <a href="{{ hits[0].url }}" class="text-blue-600 underline" target="_blank">{{ hits[0].url }}</a></p>
          <p><strong class="text-slate-700">Designation:</strong> {{ hits[0].designation or '—' }}</p>
          <p><strong class="text-slate-700">Current Company:</strong> {{ hits[0].company or '—' }}</p>
          <p><strong>Skillset:</strong> {{ hits[0].skills or "N/A" }}</p>
          <p><strong class="text-slate-700">Contact Number:</strong> {{ hits[0].phones[0] if hits[0].phones else 'N/A' }}</p>
        </div>

        {% if reco %}
        <div class="mt-6 border border-green-300 bg-green-50 p-5 rounded-md shadow-sm">
          <h2 class="text-green-800 font-semibold mb-2">📈 Business Recommendations</h2>
          <ul class="list-disc pl-5 space-y-1 text-sm text-slate-700 whitespace-pre-line">
            {% for line in reco.splitlines() %}
              {% if line.strip() %}
                <li>{{ line.strip() }}</li>
              {% endif %}
            {% endfor %}
          </ul>
        </div>
        {% endif %}
      {% else %}
        <div class="text-center text-red-600 font-medium bg-red-50 border border-red-200 rounded-md p-4 mt-6">
          ⚠️ No results found for "{{ q }}".
        </div>
      {% endif %}
    {% endif %}

    {% if total_pages > 1 %}
    <div class="mt-8 flex justify-center items-center gap-2 text-sm">
      {% for p in range(1, total_pages + 1) %}
        <a href="/?q={{ q }}&page={{ p }}"
           class="px-3 py-1 rounded-md border {{ 'bg-indigo-600 text-white border-indigo-600' if p == page else 'bg-white text-indigo-700 border-slate-300 hover:bg-slate-100' }} transition">
          {{ p }}
        </a>
      {% endfor %}
    </div>
    {% endif %}
  </div>

  <footer class="text-center text-xs text-slate-600 mt-10 pb-8">
    ALix - AI for Lead Insights & Experience &copy; 2025
  </footer>

  <script>
    function showLoading() {
      document.getElementById("spinner").classList.remove("hidden");
    }
  </script>
</body>
</html>
"""



# #/ALix_AI_for_Lead_Insights/ui_template.py
# HTML = """
# <!doctype html>
# <html lang="en">
# <head>
#   <meta charset="UTF-8">
#   <title>ALix - AI for Lead Insights & Experience</title>
#   <link rel="icon" href="/static/alix_logo.png">
#   <script src="https://cdn.tailwindcss.com"></script>
#   <script>
#     function showLoading() {
#       document.getElementById("spinner").classList.remove("hidden");
#     }
#   </script>
# </head>
# <body class="bg-gradient-to-br from-indigo-50 to-white min-h-screen font-sans">
#   <div class="max-w-4xl mx-auto py-8 px-4">
#     <div class="flex items-center justify-between mb-6">
#       <h1 class="text-2xl font-bold text-indigo-700 flex items-center gap-3">
#         <img src="/static/alix_logo.png" class="w-10 h-10"> ALix - AI for Lead Insights
#       </h1>
#       <a href="/clear" class="text-red-600 text-sm hover:underline">🗑 Clear DB</a>
#     </div>

#     <form method="POST" class="flex gap-3" onsubmit="showLoading()">
#       <input name="q" value="{{ q }}" placeholder="Enter name or company"
#              class="flex-1 border border-indigo-300 rounded px-4 py-2" required>
#       <button class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded">
#         Search
#       </button>
#     </form>

#     <div id="spinner" class="text-center my-6 hidden">
#       <p class="text-indigo-600 text-sm font-medium">⏳ Fetching info, please wait...</p>
#     </div>

#     {% if hits is not none %}
#       {% if hits %}
#         <div class="bg-white border border-indigo-200 p-4 rounded shadow mt-6 text-sm text-gray-800 space-y-2">
#           <p><strong>Name:</strong> {{ hits[0].designation or "—" }}</p>
#           <p><strong>Link:</strong> <a href="{{ hits[0].url }}" class="text-blue-600 underline" target="_blank">{{ hits[0].url }}</a></p>
#           <p><strong>Designation:</strong> {{ hits[0].designation or "—" }}</p>
#           <p><strong>Current Company:</strong> {{ hits[0].company or "—" }}</p>
#           <p><strong>Contact Number:</strong> {{ hits[0].phones[0] if hits[0].phones else "N/A" }}</p>
#         </div>

#         {% if reco %}
#         <div class="mt-6 bg-green-50 border border-green-200 p-4 rounded text-sm">
#           <h2 class="text-green-700 font-semibold mb-2">📈 Recommendations</h2>
#           <ul class="list-disc pl-6 text-gray-700 whitespace-pre-line">
#             {% for line in reco.splitlines() %}
#               {% if line.strip() %}
#                 <li>{{ line.strip() }}</li>
#               {% endif %}
#             {% endfor %}
#           </ul>
#         </div>
#         {% endif %}
#       {% else %}
#         <p class="text-red-600 mt-6">No results found for “{{ q }}”.</p>
#       {% endif %}
#     {% endif %}
#   </div>
# </body>
# </html>
# """



# HTML = """
# <!doctype html>
# <html>
# <head>
#   <meta charset="utf-8">
#   <title>ALix -AI for Lead Insights & Experience</title>
#   <script src="https://cdn.tailwindcss.com"></script>
# </head>
# <body class="bg-gray-50 min-h-screen p-8">
# <div class="max-w-5xl mx-auto bg-white rounded-xl shadow p-8">
#   <div class="flex justify-between items-center mb-4">
#     <h1 class="text-2xl font-bold text-blue-700">ALix -AI for Lead Insights & Experience</h1>
#     <div class="flex items-center gap-4">
#       <a href="/clear" class="text-sm text-red-600 hover:underline">🗑 Clear All</a>
#     </div>
#   </div>

#   <form method="POST" class="flex gap-2 mb-4">
#     <input name="q" value="{{ q }}" class="flex-1 border border-blue-300 rounded px-3 py-2" placeholder="e.g. Sundar Pichai" required>
#     <button class="bg-blue-600 text-white px-4 py-2 rounded">Search</button>
#   </form>

#   {% if hits %}
#     <table class="table-auto w-full text-sm border mb-6">
#       <thead class="bg-blue-100"><tr>
#         <th class="p-2 text-left">Profile</th>
#         <th class="p-2 text-left">Designation</th>
#         <th class="p-2 text-left">Company</th>
#         <th class="p-2 text-left">Location</th>
#         <th class="p-2 text-left">Phones</th>
#       </tr></thead>
#       <tbody>
#         {% for h in hits %}
#         <tr class="border-t">
#           <td class="p-2"><a href="{{ h.url }}" target="_blank" class="text-blue-600 underline">Link</a></td>
#           <td class="p-2">{{ h.designation or "—" }}</td>
#           <td class="p-2">{{ h.company or "—" }}</td>
#           <td class="p-2">{{ h.location or "—" }}</td>
#           <td class="p-2">{{ h.phones | join(", ") if h.phones else "N/A" }}</td>
#         </tr>
#         {% endfor %}
#       </tbody>
#     </table>
#   {% elif hits is not none %}
#     <p class="text-red-600 font-medium">No results found.</p>
#   {% endif %}

#   {% if reco %}
#     <h2 class="text-lg font-semibold mb-2 text-green-700">📈 Recommendations</h2>
#     <div class="bg-green-50 border border-green-200 rounded p-4 text-sm whitespace-pre-line">
#       {{ reco }}
#     </div>
#   {% endif %}

#   {% if total_pages > 1 %}
#     <div class="mt-6 flex gap-2 justify-center">
#       {% for p in range(1, total_pages + 1) %}
#         <a href="/?q={{ q }}&page={{ p }}" class="px-3 py-1 rounded border {{ 'bg-blue-600 text-white' if page == p else 'bg-white text-blue-700 border-blue-300' }}">{{ p }}</a>
#       {% endfor %}
#     </div>
#   {% endif %}
# </div>
# </body>
# </html>
# """



