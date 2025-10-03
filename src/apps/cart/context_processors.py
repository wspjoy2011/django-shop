def cart_summary(request):
    cart = getattr(request, "cart", None)

    return {"cart": cart}
