from hub.ui.common.design import Icon
needed = ['house','grid','search','monitor','lightbulb','file-text',
          'alert-circle','book-open','users-round','bar-chart',
          'shield-lock','user-cog','globe','moon','sun','bell',
          'settings','logout','panel-left']
missing = [n for n in needed if n not in Icon._PATHS]
print("MISSING:", missing if missing else "None - all OK")
for n in needed:
    status = "OK" if n in Icon._PATHS else "MISSING"
    print(f"  {status}: {n}")
