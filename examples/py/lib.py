def Fib(n):
  if n in [0, 1]:
    return 1
  else:
    return Fib(n-1) + Fib(n-2)
