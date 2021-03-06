from django.core.exceptions import ObjectDoesNotExist
import os

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db import transaction
from django.db.models import ProtectedError
from django.http import HttpResponse

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.core import serializers


from datetime import datetime

from wood.models import *


def index(request):
    cart = Cart(request)
    quantity_in_cart = len(cart)
    return render(request, 'index.html', {'quantity_in_cart': quantity_in_cart})


def view_cart(request):
    cart = Cart(request)
    quantity_in_cart = len(cart)
    concrete_products = []
    for cp_id, cp_quantity in cart.cart.items():
        cp = ConcreteProduct.objects.get(pk=cp_id)
        concrete_products.append((cp, cp_quantity, cp.price * cp_quantity))
    context = {'quantity_in_cart': quantity_in_cart,
               'concrete_products': concrete_products,
               'summary_price': cart.get_summary_price()}
    return render(request, 'view_cart.html', context)


def get_categories(request):
    cart = Cart(request)
    quantity_in_cart = len(cart)
    categories = Category.objects.all()
    context = {'categories': categories,
               'quantity_in_cart': quantity_in_cart}
    return render(request, 'view_catalog.html', context)


def get_products_in_category(request, category_id):
    cart = Cart(request)
    quantity_in_cart = len(cart)
    category = Category.objects.get(pk=category_id)
    products = Product.objects.filter(category_id=category_id)
    context = {'products': products, 'category': category,
               'quantity_in_cart': quantity_in_cart}
    return render(request, 'view_products_in_category.html', context)


def create_category(request):
    if request.method == 'GET':
        return render(request, 'create_category.html')
    elif request.method == 'POST':
        image_file = request.FILES['image']
        category = Category(name=request.POST['name'],
                            description=request.POST['comment'],
                            image=image_file)
        category.save()
        return redirect('get_categories')


def edit_category(request, category_id):
    category = Category.objects.get(pk=category_id)
    if request.method == 'POST':
        image_file = request.FILES.get('image', False)
        if image_file:
            category.image.delete(save=True)
            category.image = image_file
        category.name = request.POST['name']
        category.description = request.POST['comment']
        category.save()
        return redirect('get_categories')
    else:
        context = {'category': category}
        return render(request, 'edit_category.html', context)


def delete_category(request, category_id):
    category = Category.objects.get(pk=category_id)
    if Product.objects.filter(category=category).exists():
        return error(request, 'Невозможно удалить категорию в которой есть продукты')
    category.image.delete(save=True)
    category.delete()
    return redirect('get_categories')


def create_product(request, category_id):
    if request.method == 'GET':
        context = {'category_id': category_id}
        return render(request, 'create_product.html', context)
    elif request.method == 'POST':
        image_file = request.FILES['image']
        category = Category.objects.get(pk=category_id)
        product = Product(category=category,
                          name=request.POST['name'],
                          description=request.POST['comment'],
                          product_image=image_file,
                          visible=False)
        product.save()
        return redirect('category_content', category_id)


def edit_product(request, category_id, product_id):
    if request.method == 'GET':
        context = {'category_id': category_id, 'product': Product.objects.get(pk=product_id)}
        return render(request, 'edit_product.html', context)
    elif request.method == 'POST':
        product = Product.objects.get(pk=product_id)
        product.name = request.POST['name']
        product.description = request.POST['comment']
        image_file = request.FILES.get('image', False)
        if image_file:
            product.product_image.delete(save=True)
            product.product_image = image_file
        product.save()
        return redirect('view_product', category_id, product_id)


def delete_product(request, category_id, product_id):
    product = Product.objects.get(pk=product_id)
    if ConcreteProduct.objects.filter(product=product).exists():
        return error(request, 'В удаляемом изделии существуют конкретные изделия')
    product.delete()
    return redirect('category_content', category_id)


def view_product(request, category_id, product_id):
    cart = Cart(request)
    quantity_in_cart = len(cart)
    product = Product.objects.get(pk=product_id)
    concrete_products = ConcreteProduct.objects.filter(product_id=product_id)
    materials = Material.objects.filter(concreteproduct__product=product).distinct()
    sizes = Size.objects.filter(concreteproduct__product=product,
                                concreteproduct__material=materials.first()).distinct()
    coatings = Coating.objects.filter(concreteproduct__product=product,
                                      concreteproduct__size=sizes.first()).distinct()

    concrete_product = ConcreteProduct.objects.filter(product_id=product_id,
                                                      material=materials.first(),
                                                      size=sizes.first(),
                                                      coating=coatings.first())
    context = {'category_id': category_id,
               'product': product,
               'concrete_products': concrete_products,
               'materials': materials,
               'sizes': sizes,
               'coatings': coatings,
               'quantity_in_cart': quantity_in_cart
               }
    if not concrete_product.first():
        context['concrete_product'] = False
    else:
        context['concrete_product'] = concrete_product.first()
    return render(request, 'view_product.html', context)


def create_concrete_product(request, category_id, product_id):
    if request.method == 'GET':
        materials = Material.objects.all()
        sizes = Size.objects.all()
        coatings = Coating.objects.all()
        context = {'category_id': category_id,
                   'product_id': product_id,
                   'materials': materials,
                   'sizes': sizes,
                   'coatings': coatings
                   }
        return render(request, 'create_concrete_product.html', context)
    elif request.method == 'POST':
        product = Product.objects.get(pk=product_id)
        product.visible = True
        product.save()
        material = Material.objects.get(pk=request.POST['materials'])
        coating = Coating.objects.get(pk=request.POST['coatings'])
        size = Size.objects.get(pk=request.POST['sizes'])
        concrete_product = ConcreteProduct(product=product,
                                           price=request.POST['price'],
                                           number=request.POST['amount'],
                                           time_production=request.POST['time'],
                                           material=material,
                                           coating=coating,
                                           size=size)
        concrete_product.save()
        return redirect('view_concrete_products', category_id, product_id)


def create_personal_order(request):
    if request.method == 'GET':
        cart = Cart(request)
        quantity_in_cart = len(cart)
        return render(request, 'create_personal_order.html', {'quantity_in_cart': quantity_in_cart})
    elif request.method == 'POST':
        if not request.user.is_anonymous():
            client = Client.objects.get(user=request.user)
        else:
            user = User.objects.create_user(username=request.POST['email'],
                                            email=request.POST['email'],
                                            password='change_pass',
                                            first_name=request.POST['name'],
                                            last_name=request.POST['surname'],
                                            )
            user.save()
            client = Client(user=user, telephone=request.POST['telephone'])
            client.save()
        file = request.FILES['attachments']
        need_delivery = 'isDelivered' in request.POST
        personal_order = PersonalOrder(client=client,
                                       requirements=request.POST['requirements'],
                                       attachments=file,
                                       need_delivery=need_delivery,
                                       delivery_address=request.POST['delivery_address'],
                                       payment_type=request.POST['payment'])
        personal_order.save()
        return redirect('index')


def create_material(request):
    if request.method == 'GET':
        return render(request, 'create_material.html')
    elif request.method == 'POST':
        material = Material(name=request.POST['name'],
                            description=request.POST['description'],
                            amount=request.POST['amount'])
        material.save()
        return redirect('get_materials')


def create_coating(request):
    if request.method == 'GET':
        return render(request, 'create_coating.html')
    elif request.method == 'POST':
        coating = Coating(name=request.POST['name'],
                          description=request.POST['description'])
        coating.save()
        return redirect('get_coatings')


def create_size(request):
    if request.method == 'GET':
        return render(request, 'create_size.html')
    elif request.method == 'POST':
        size = Size(length=request.POST['length'],
                    width=request.POST['width'],
                    height=request.POST['height'],
                    weight=request.POST['weight'])
        size.save()
        return redirect('get_sizes')


def view_profile(request):
    cart = Cart(request)
    quantity_in_cart = len(cart)
    user = request.user
    client = Client.objects.get(user=user)
    if request.method == 'GET':
        context = {'username': user.username,
                   'last_name': user.last_name,
                   'first_name': user.first_name,
                   'email': user.email,
                   'skype': client.skype,
                   'telephone': client.telephone,
                   'postcode': client.postcode,
                   'address': client.address,
                   'quantity_in_cart': quantity_in_cart}
        return render(request, 'view_profile.html', context)
    else:
        user.first_name = request.POST['first_name']
        user.last_name = request.POST['last_name']
        user.email = request.POST['email']
        user.save()
        client.skype = request.POST['skype']
        client.telephone = request.POST['telephone']
        client.postcode = request.POST['postcode']
        client.address = request.POST['address']
        client.save()
        return redirect('view_profile')


def view_orders(request):
    cart = Cart(request)
    quantity_in_cart = len(cart)
    client = Client.objects.get(user=request.user)
    personal_orders = PersonalOrder.objects.filter(client=client).order_by('-date')
    orders = Order.objects.filter(client=client).order_by('-date')
    context = {'personal_orders': personal_orders,
               'orders': orders,
               'quantity_in_cart': quantity_in_cart}
    return render(request, 'view_orders.html', context)


def view_all_orders(request):
    cart = Cart(request)
    quantity_in_cart = len(cart)
    personal_orders = PersonalOrder.objects.all()
    orders = Order.objects.all().order_by('status', '-date')
    context = {'personal_orders': personal_orders,
               'orders': orders,
               'quantity_in_cart': quantity_in_cart}
    return render(request, 'view_all_orders.html', context)


def registration(request):
    if request.method == 'GET':
        cart = Cart(request)
        quantity_in_cart = len(cart)
        return render(request, 'create_user.html', {'quantity_in_cart': quantity_in_cart})
    else:
        try:
            user = User.objects.create_user(username=request.POST['username'],
                                            email=request.POST['email'],
                                            password=request.POST['password'],
                                            first_name=request.POST['first_name'],
                                            last_name=request.POST['last_name'],
                                            )
            user.save()
        except IntegrityError:
            return error(request, 'Пользователь с таким никнеймом уже существует')
        client = Client(user=user,
                        telephone=request.POST['telephone'],
                        skype=request.POST['skype'],
                        postcode=request.POST['postcode'],
                        address=request.POST['address'])

        client.save()
        return redirect('index')


def login_user(request):
    try:
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user.is_active:
            login(request, user)
    except AttributeError:
        return error(request, 'Неверный пароль')
    return redirect('index')


def logout_user(request):
    logout(request)
    return redirect('index')


def view_materials(request):
    materials = Material.objects.all()
    context = {'materials': materials}
    return render(request, 'view_materials.html', context)


def delete_material(request, material_id):
    material = Material.objects.get(pk=material_id)
    try:
        material.delete()
    except ProtectedError:
        return error(request, 'Удаляемый материал используется для изделий')
    return redirect('get_materials')


def edit_material(request, material_id):
    material = Material.objects.get(pk=material_id)
    if request.method == 'POST':
        material.name = request.POST['name']
        material.description = request.POST['description']
        material.amount = request.POST['amount']
        material.save()
        return redirect('get_materials')
    else:
        context = {'material': material}
        return render(request, 'edit_material.html', context)


def view_coatings(request):
    coatings = Coating.objects.all()
    context = {'coatings': coatings}
    return render(request, 'view_coatings.html', context)


def delete_coatings(request, coating_id):
    coating = Coating.objects.get(pk=coating_id)
    try:
        coating.delete()
    except ProtectedError:
        return error(request, 'Удаляемое покрытие используется для изделий')
    return redirect('get_coatings')


def edit_coating(request, coating_id):
    coating = Coating.objects.get(pk=coating_id)
    if request.method == 'POST':
        coating.name = request.POST['name']
        coating.description = request.POST['description']
        coating.save()
        return redirect('get_coatings')
    else:
        context = {'coating': coating}
        return render(request, 'edit_coating.html', context)


def get_sizes(request):
    sizes = Size.objects.all()
    context = {'sizes': sizes}
    return render(request, 'view_sizes.html', context)


def delete_size(request, size_id):
    size = Size.objects.get(pk=size_id)
    try:
        size.delete()
    except ProtectedError:
        return error(request, 'Удаляемый размер используется для изделий')
    return redirect('get_sizes')


def edit_size(request, size_id):
    size = Size.objects.get(pk=size_id)
    if request.method == 'POST':
        size.length = request.POST['length']
        size.width = request.POST['width']
        size.height = request.POST['height']
        size.weight = request.POST['weight']
        size.save()
        return redirect('get_sizes')
    else:
        context = {'size': size}
        return render(request, 'edit_size.html', context)


def ajax_update_for_materials(request, product_id):
    data = dict()
    name_material = request.GET['name_material']
    material = Material.objects.get(name=name_material)
    product = Product.objects.get(pk=product_id)
    sizes = Size.objects. \
        filter(concreteproduct__material=material, concreteproduct__product=product).distinct()
    coatings = Coating.objects. \
        filter(concreteproduct__material=material,
               concreteproduct__product=product,
               concreteproduct__size=sizes.first()).distinct()
    concrete_product = ConcreteProduct.objects.get(material=material,
                                                   product=product,
                                                   size=sizes.first(),
                                                   coating=coatings.first())

    data['form_is_valid'] = True
    data['sizes'] = serializers.serialize('json', sizes)
    data['coatings'] = serializers.serialize('json', coatings)
    data['price'] = concrete_product.price
    data['amount'] = concrete_product.number
    data['concrete_product_id'] = concrete_product.id

    return JsonResponse(data)


def ajax_update_for_sizes(request, product_id):
    data = dict()

    name_material = request.GET['name_material']
    name_size = request.GET['name_size']
    all_size = str(name_size).split('x')

    size = Size.objects.get(width=all_size[0], height=all_size[1], length=all_size[2])
    material = Material.objects.get(name=name_material)
    product = Product.objects.get(pk=product_id)

    coatings = Coating.objects. \
        filter(concreteproduct__material=material, concreteproduct__product=product, concreteproduct__size=size)

    concrete_product = ConcreteProduct.objects.get(material=material,
                                                   product=product,
                                                   size=size,
                                                   coating=coatings.last())

    data['form_is_valid'] = True
    data['coatings'] = serializers.serialize('json', coatings)
    data['price'] = concrete_product.price
    data['amount'] = concrete_product.number
    data['concrete_product_id'] = concrete_product.id

    return JsonResponse(data)


def ajax_update_for_coatings(request, product_id):
    data = dict()

    name_material = request.GET['name_material']
    name_coating = request.GET['name_coating']
    name_size = request.GET['name_size']
    all_size = str(name_size).split('x')

    material = Material.objects.get(name=name_material)
    coating = Coating.objects.get(name=name_coating)
    size = Size.objects.get(width=all_size[0], height=all_size[1], length=all_size[2])
    product = Product.objects.get(pk=product_id)

    concrete_product = ConcreteProduct.objects.get(material=material,
                                                   product=product,
                                                   size=size,
                                                   coating=coating)
    data['form_is_valid'] = True
    data['price'] = concrete_product.price
    data['amount'] = concrete_product.number
    data['concrete_product_id'] = concrete_product.id

    return JsonResponse(data)


def ajax_add_to_cart(request):
    data = dict()
    cart = Cart(request)
    cp_id = request.GET['id']
    concrete_product = ConcreteProduct.objects.get(pk=cp_id)
    data['form_is_valid'] = True
    cart.add_concrete_product(concrete_product)
    data['quantity'] = len(cart)
    return JsonResponse(data)


def delete_from_cart(request, cp_id):
    data = dict()
    cart = Cart(request)
    cart.remove(cp_id)
    return redirect('view_cart')


def ajax_update_cart(request):
    data = dict()
    cart = Cart(request)
    cp_id = request.POST['id']
    quantity = request.POST['quantity']
    concrete_product = ConcreteProduct.objects.get(pk=cp_id)
    data['form_is_valid'] = True
    cart.add_concrete_product(concrete_product, int(quantity), update=True)
    data['quantity'] = len(cart)
    data['price'] = concrete_product.price * int(quantity)
    data['summary_price'] = cart.get_summary_price()
    return JsonResponse(data)


def ajax_update_amount(request):
    data = dict()
    cp_id = request.POST['id']
    quantity = request.POST['quantity']
    concrete_product = ConcreteProduct.objects.get(pk=cp_id)
    concrete_product.number = quantity
    concrete_product.save()
    data['form_is_valid'] = True
    return JsonResponse(data)


def ajax_change_status_order(request):
    data = dict()
    id = request.POST['id']
    status = request.POST['status']
    order = Order.objects.get(pk=id)
    order.status = status
    order.save()
    data['form_is_valid'] = True
    return JsonResponse(data)


def ajax_change_status_personal_order(request):
    data = dict()
    id = request.POST['id']
    status = request.POST['status']
    personal_order = PersonalOrder.objects.get(pk=id)
    personal_order.status = status
    personal_order.save()
    data['form_is_valid'] = True
    return JsonResponse(data)


def view_concrete_products(request, category_id, product_id):
    # product = Product.objects.get(pk=product_id)
    concrete_products = ConcreteProduct.objects.filter(product_id=product_id)
    context = {'concrete_products': concrete_products,
               'category_id': category_id,
               'product': Product.objects.get(pk=product_id)}
    return render(request, 'view_concrete_products.html', context)


def delete_concrete_product(request, category_id, product_id, concrete_product_id):
    concrete_product = ConcreteProduct.objects.get(pk=concrete_product_id)
    concrete_product.delete()
    return redirect('view_concrete_products', category_id, product_id)


@login_required
def change_password(request):
    if request.is_ajax():
        try:
            user = User.objects.get(username=request.user.username)

        except User.DoesNotExist:
            return HttpResponse('USER_NOT_FOUND')
        else:
            if not user.check_password(request.POST['old_password']):
                return HttpResponse('Неверный пароль')
            if request.POST['new_password'] != request.POST['confirm_password']:
                return HttpResponse('Пароли не совпадают')
            user.set_password(request.POST['new_password'])
            user.save()

            user = authenticate(username=request.user.username, password=request.POST['new_password'])
            if user.is_active:
                login(request, user)
            return HttpResponse('OK')
    else:
        return HttpResponse(status=400)


def error(request, error_message):
    return render(request, 'error_page.html', context={'error_message': error_message})


def download_attachments(request, order_id):
    order = PersonalOrder.objects.get(pk=order_id)

    file_path = order.attachments.url[1:]
    with open(file_path, 'rb') as fh:
        response = HttpResponse(fh.read(), content_type='application/')
        response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
        return response


@login_required
def get_requirements(request, order_id):
    if request.is_ajax():
        try:
            user = User.objects.get(username=request.user.username)

        except User.DoesNotExist:
            return HttpResponse('USER_NOT_FOUND')
        else:
            order = PersonalOrder.objects.get(pk=order_id)
            return HttpResponse(order.requirements)
    else:
        return HttpResponse(status=400)


def change_personal_order(request):
    order = PersonalOrder.objects.get(pk=request.POST['order_id'])
    order.payment_type = request.POST['payment']
    need_delivery = 'isDelivered' in request.POST
    order.need_delivery = need_delivery
    order.delivery_address = request.POST['delivery_address']
    order.save()
    return redirect('view_orders')


def cancel_personal_order(request, order_id):
    order = PersonalOrder.objects.get(pk=order_id)
    order.status = 'Отменен'
    order.save()
    return redirect('view_orders')


@transaction.atomic
def create_order(request):
    cart = Cart(request)
    need_delivery = 'isDelivered' in request.POST
    client = Client.objects.get(user=request.user)
    order = Order(need_delivery=need_delivery,
                  delivery_address=request.POST['delivery_address'],
                  payment_type=request.POST['payment'],
                  client=client)
    order.save()
    for cp_id, cp_quantity in cart.cart.items():
        cp = ConcreteProduct.objects.get(pk=cp_id)
        position_in_order = PositionInOrder(order=order,
                                            concrete_product=cp,
                                            amount=cp_quantity,
                                            price=cp.price)
        position_in_order.save()
        cp.number -= cp_quantity
        cp.save()
    cart.clear()
    return redirect('view_orders')


@transaction.atomic
def cancel_order(request, order_id):
    order = Order.objects.get(pk=order_id)
    positions = PositionInOrder.objects.filter(order=order)
    for position in positions:
        position.concrete_product.number += position.amount
        position.concrete_product.save()
    order.status = 'Отменен'
    order.save()

    return redirect('view_orders')


def view_order(request, order_id):
    cart = Cart(request)
    quantity_in_cart = len(cart)
    order = Order.objects.get(pk=order_id)
    positions = PositionInOrder.objects.filter(order=order)
    summary_price = 0
    for position in positions:
        summary_price += (position.price * position.amount)
    context = {'quantity_in_cart': quantity_in_cart,
               'positions': positions,
               'summary_price': summary_price}
    return render(request, 'view_concrete_order.html', context)


def change_order(request):
    order = Order.objects.get(pk=request.POST['order_id'])
    order.payment_type = request.POST['payment']
    need_delivery = 'isDelivered' in request.POST
    order.need_delivery = need_delivery
    order.delivery_address = request.POST['delivery_address']
    order.save()
    return redirect('view_orders')


def view_report(request, select_value):
    amount_concrete_products = dict()
    period = datetime.datetime.now()
    if select_value == '1':
        period -= datetime.timedelta(1)
    elif select_value == '2':
        period -= datetime.timedelta(7)
    elif select_value == '3':
        period -= datetime.timedelta(31)
    elif select_value == '4':
        period -= datetime.timedelta(365)
    if select_value == '5':
        all_parts_of_orders = PositionInOrder.objects.all()
    else:
        all_parts_of_orders = PositionInOrder.objects.filter(order__date__gt=period)
    for part in all_parts_of_orders:
        if amount_concrete_products.get(str(part.concrete_product.id)) is None:
            amount_concrete_products[str(part.concrete_product.id)] = 0
        amount_concrete_products[str(part.concrete_product.id)] += part.amount
    list_amounts = []
    for cp_id, amount in amount_concrete_products.items():
        cp = ConcreteProduct.objects.get(pk=cp_id)
        cat_name = Category.objects.get(product__concreteproduct=cp).name
        list_amounts.append((cp, amount, amount*cp.price, cat_name))
    list_amounts.sort(key=lambda x: x[1], reverse=True)
    return render(request, 'view_report.html', {'list_amounts': list_amounts, 'selected_value': select_value})


def ajax_update_report(request):
    data = dict()
    punkt = request.GET['period']
    amount_concrete_products = dict()
    period = datetime.datetime.now()
    if punkt == '1':
        period -= datetime.timedelta(1)
    elif punkt == '2':
        period -= datetime.timedelta(7)
    elif punkt == '3':
        period -= datetime.timedelta(31)
    elif punkt == '4':
        period -= datetime.timedelta(365)
    if punkt == '5':
        all_orders = Order.objects.all()
    else:
        all_orders = Order.objects.filter(date__gt=period)
    all_parts_of_orders = PositionInOrder.objects.all()
    parts_of_orders = []
    for order in all_orders:
        for part in all_parts_of_orders:
            if part.order == order:
                parts_of_orders.append(part)
    for part in parts_of_orders:
        if amount_concrete_products.get(str(part.concrete_product.id)) is None:
            amount_concrete_products[str(part.concrete_product.id)] = 0
        amount_concrete_products[str(part.concrete_product.id)] += part.amount
    list_amounts = []
    for cp_id, amount in amount_concrete_products.items():
        cp = ConcreteProduct.objects.get(pk=cp_id)
        list_amounts.append((cp, amount, amount*cp.price))
    data['form_is_valid'] = True
    data['list_amounts'] = list_amounts
    return render(request, 'view_report.html', {'list_amounts': list_amounts})


def ajax_update_cost_delivery(request):
    data = dict()
    order_id = request.POST['id']
    cost = request.POST['cost']
    order = Order.objects.get(pk=order_id)
    order.cost_delivery = cost
    order.save()
    data['form_is_valid'] = True
    return JsonResponse(data)


def ajax_update_date_delivery(request):
    data = dict()
    order_id = request.POST['id']
    date = request.POST['date']
    order = Order.objects.get(pk=order_id)
    order.date_delivery = date
    order.save()
    data['form_is_valid'] = True
    return JsonResponse(data)