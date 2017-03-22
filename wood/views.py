import os

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect

from wood.models import *
from wood_site.settings import STATIC_URL


def index(request):
    return render(request, 'index.html')


def get_categories(request):
    categories = Category.objects.all()
    context = {"categories": categories}
    return render(request, "view_catalog.html", context)


def get_products_in_category(request, category_id):
    category = Category.objects.get(pk=category_id)
    products = Product.objects.filter(category_id=category_id)
    context = {"products": products, "category": category}
    return render(request, "view_products_in_category.html", context)


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
        context = {"category": category}
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
        context = {"category_id": category_id}
        return render(request, 'create_product.html', context)
    elif request.method == 'POST':
        image_file = request.FILES['image']
        category = Category.objects.get(pk=category_id)
        product = Product(category=category,
                          name=request.POST['name'],
                          description=request.POST['comment'],
                          product_image=image_file)
        product.save()
        return redirect('get_categories')


def get_product(request, category_id, product_id):
    product = Product.objects.get(pk=product_id)
    concrete_products = ConcreteProduct.objects.filter(product_id=product_id)
    materials = Material.objects.all()
    for material in materials:
        remove = True
        for p in concrete_products:
            if material.id == p.material_id:
                remove = False
        if remove:
            materials.filter(id=material.id)
    sizes = Size.objects.all()
    coatings = Coating.objects.all()
    context = {'category_id': category_id,
               'product': product,
               'concrete_products': concrete_products,
               'materials': materials,
               'sizes': sizes,
               'coatings': coatings,
               }
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
        return redirect('get_categories')


def create_personal_order(request):
    if request.method == 'GET':
        return render(request, 'create_personal_order.html')
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
        personal_order = PersonalOrder(client=client,
                                       requirements=request.POST['requirements'],
                                       attachments=file)
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
                   'address': client.address}
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
    client = Client.objects.get(user=request.user)
    personal_orders = PersonalOrder.objects.filter(client=client)
    context = {'personal_orders': personal_orders}
    return render(request, 'view_orders.html', context)


def registration(request):
    if request.method == 'GET':
        return render(request, 'create_user.html')
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
    except AttributeError:
        return error(request, 'Неверный пароль')
    if user.is_active:
        login(request, user)
    return redirect('index')


def logout_user(request):
    logout(request)
    return redirect('index')


def ajax_update_product(request, category_id, product_id):
    '''name_material = request.GET['material']
    material = Material.objects.get(name=name_material)
    product = Product.objects.get(pk=product_id)
    concrete_products = ConcreteProduct.objects.filter(material=material).filter(product=product)
    '''
    data = dict()
    data['form_is_valid'] = True
    return JsonResponse(data)


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
        context = {"material": material}
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
        context = {"coating": coating}
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
        context = {"size": size}
        return render(request, 'edit_size.html', context)


@login_required
def change_password(request):
    if request.is_ajax():
        try:
            user = User.objects.get(username=request.user.username)

        except User.DoesNotExist:
            return HttpResponse("USER_NOT_FOUND")
        else:
            if not user.check_password(request.POST['old_password']):
                return HttpResponse("Неверный пароль")
            if request.POST['new_password'] != request.POST['confirm_password']:
                return HttpResponse("Пароли не совпадают")
            user.set_password(request.POST['new_password'])
            user.save()

            user = authenticate(username=request.user.username, password=request.POST['new_password'])
            if user.is_active:
                login(request, user)
            return HttpResponse("OK")
    else:
        return HttpResponse(status=400)


def error(request, error_message):
    return render(request, 'error_page.html', context={'error_message': error_message})


def download_attachments(request, order_id):
    order = PersonalOrder.objects.get(pk=order_id)

    file_path = order.attachments.url[1:]
    with open(file_path, 'rb') as fh:
        response = HttpResponse(fh.read(), content_type="application/")
        response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
        return response


@login_required
def get_requirements(request, order_id):
    if request.is_ajax():
        try:
            user = User.objects.get(username=request.user.username)

        except User.DoesNotExist:
            return HttpResponse("USER_NOT_FOUND")
        else:
            order = PersonalOrder.objects.get(pk=order_id)
            return HttpResponse(order.requirements)
    else:
        return HttpResponse(status=400)
