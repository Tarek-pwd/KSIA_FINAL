from vec_reporting import run_query, reset_agent

# First query - agent will be created here
user_query1 = 'أرغب في تعبئة نموذج خطاب استقالة باسمي "سليمان بن راشد المطيري"، بتاريخ 1446/04/20 هـ، برتبة رقيب، الرقم العسكري 281930، وذلك بسبب ظروف عائلية قاهرة تتطلب تفرغي التام في هذه الفترة. خدمتي العسكرية استمرت لمدة 12 سنة.'
result1 = run_query(user_query1)
print(result1)

reset_agent()
