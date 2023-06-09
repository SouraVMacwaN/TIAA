from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django import forms
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from .models import Auction, Bid , Category, Image, User
from .forms import AuctionForm, ImageForm, CommentForm, BidForm, LoginForm, UserRegistrationForm,productForm
from .models import *
from django.http import JsonResponse
import json
import datetime

def register(request):
    
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            # Create a new user object but avoid saving it yet
            new_user = user_form.save(commit=False)
            # Set the chosen password
            new_user.set_password(
                user_form.cleaned_data['password'])
            new_user.is_farmer = user_form.cleaned_data['user_type'] == 'farmer'
            # Save the User object
            new_user.save()
            # Create the user profile
            return render(request,
                          'account/register_done.html',
                          {'new_user': new_user})
    else:
        user_form = UserRegistrationForm()
    return render(request,
                  'account/register.html',
                  {'user_form': user_form,
                   })

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request, username=cd['username'], password=cd['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponse('Authenticated successfully')
                else:
                    return HttpResponse('Disabled account')
            else:
                return HttpResponse('Invalid login')
    else:
        form = LoginForm()
        return render(request, 'account/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))

def index(request):

    if request.user.is_authenticated: 
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False) 
        items = order.orderitem_set.all() 
        cartItems = order.get_cart_items
    else: 
        items = [] 
        order = {'get_cart_total':0 , 'get_cart_items':0}
        cartItems = order['get_cart_items']

    auctions = Auction.objects.all().order_by('-date_created')
    expensive_auctions = Auction.objects.order_by('-starting_bid')[:4]
    for auction in auctions:
        auction.image = auction.get_images.first()

    page = request.GET.get('page', 1)
    paginator = Paginator(auctions, 5)

    try:
        pages = paginator.page(page)
    except PageNotAnInteger:
        pages = paginator.page(paginator.num_pages)
        
    return render (request, 'index.html', {
        'categories': Category.objects.all(),
        'auctions': auctions,
        'expensive_auctions': expensive_auctions,
        'auctions_count': Auction.objects.all().count(),
        'bids_count': Bid.objects.all().count(),
        'categories_count': Category.objects.all().count(),
        'users_count': User.objects.all().count(),
        'pages': pages,
        'title': 'Dashboard',
        'order':order,
    })

@login_required
def create_auction(request):

    if request.user.is_authenticated: 
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False) 
        items = order.orderitem_set.all() 
        cartItems = order.get_cart_items
    else: 
        items = [] 
        order = {'get_cart_total':0 , 'get_cart_items':0}
        cartItems = order['get_cart_items']

    ImageFormSet = forms.modelformset_factory(Image, form = ImageForm)
    if request.method == 'POST':
        auction_form = AuctionForm(request.POST, request.FILES)
        image_form = ImageFormSet(request.POST, request.FILES, queryset=Image.objects.none())

        if auction_form.is_valid() and image_form.is_valid():
            new_auction = auction_form.save(commit=False)
            new_auction.creator = request.user
            new_auction.save()

            for auction_form in image_form.cleaned_data:
                if auction_form:
                    image = auction_form['image']

                    new_image = Image(auction=new_auction, image=image)
                    new_image.save()

            return render(request, 'create_auction.html', {
                'categories': Category.objects.all(),
                'auction_form':AuctionForm(),
                'image_form': ImageFormSet(queryset=Image.objects.none()),
                'title': 'Create Auction',
                'success': True,
                'order':order,
            })

        else:
            return render(request, 'create_auction.html', {
                'categories':Category.objects.all(),
                'auction_form': AuctionForm(),
                'image_form':ImageFormSet(queryset=Image.objects.none()),
                'title':'Create Auction',
                'order':order,
            })
    else:
        return render(request, 'create_auction.html', {
                'categories':Category.objects.all(),
                'auction_form': AuctionForm(),
                'image_form':ImageFormSet(queryset=Image.objects.none()),
                'title':'Create Auction',
                'order':order,
            })


def active (request):

    if request.user.is_authenticated: 
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False) 
        items = order.orderitem_set.all() 
        cartItems = order.get_cart_items
    else: 
        items = [] 
        order = {'get_cart_total':0 , 'get_cart_items':0}
        cartItems = order['get_cart_items']

    '''
    It renders a page that displays all of 
    the currently active auction listings
    Active auctions are paginated: 3 per page
    '''
    category_name = request.GET.get('category_name', None)
    if category_name is not None:
        auctions = Auction.objects.filter(active=True, category=category_name).order_by('-date_created')
    else:
        auctions = Auction.objects.filter(active=True).order_by('-date_created')

    for auction in auctions:
        auction.image = auction.get_images.first()
        if request.user in auction.watchers.all():
            auction.is_watched = True
        else:
            auction.is_watched = False

    # Show 3 active auctions per page
    page = request.GET.get('page', 1)
    paginator = Paginator(auctions, 8)
    try:
        pages = paginator.page(page)
    except PageNotAnInteger:
        pages = paginator.page(1)
    except EmptyPage:
        pages = paginator.page(paginator.num_pages)

    return render(request, 'active.html', {
        'categories': Category.objects.all(),
        'auctions': auctions,
        'auctions_count': auctions.count(),
        'pages': pages,
        'title': 'Active Auctions',
        'order':order,
    })

@login_required
def watchlist(request):

    if request.user.is_authenticated: 
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False) 
        items = order.orderitem_set.all() 
        cartItems = order.get_cart_items
    else: 
        items = [] 
        order = {'get_cart_total':0 , 'get_cart_items':0}
        cartItems = order['get_cart_items']


    #displays all auctions that they have added on their watchlist

    auctions = request.user.watchlist.all()

    for auction in auctions:
        auction.image = auction.get_images.first()

        if request.user in auction.watchers.all():
            auction.is_watched = True
        else:
            auction.is_watched = False
        
    page = request.GET.get('page', 1)
    paginator = Paginator(auctions, 3)
    try:
        pages = paginator.page(page)
    except PageNotAnInteger:
        pages = paginator.page(1)
    except EmptyPage:
        pages = paginator.page(paginator.num_pages)

    return render(request, 'active.html', {
        'categories':Category.objects.all(),
        'auctions':auctions,
        'auctions_count':auctions.count(),
        'pages':pages,
        'title':'Watchlist',
        'order':order,
    })

@login_required
def watchlist_edit(request, auction_id, reverse_method):


    #allows users to add/remove items to/from watchlist

    auction = Auction.objects.get(id=auction_id)

    if request.user in auction.watchers.all():
        auction.watchers.remove(request.user)
    else:
        auction.watchers.add(request.user)

    if reverse_method == 'auction_detail':
        return auction_detail(request, auction_id)
    else:
        return HttpResponseRedirect(reverse(reverse_method))

def auction_detail(request, auction_id):

    if request.user.is_authenticated: 
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False) 
        items = order.orderitem_set.all() 
        cartItems = order.get_cart_items
    else: 
        items = [] 
        order = {'get_cart_total':0 , 'get_cart_items':0}
        cartItems = order['get_cart_items']

    #displays the content of an auction

    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('login'))

    auction = Auction.objects.get(id=auction_id)

    if request.user in auction.watchers.all():
        auction.is_watched = True

    else: 
        auction.is_watched = False

    return render(request, 'auction.html', {
        'categories': Category.objects.all(),
        'auction':auction,
        'images':auction.get_images.all(),
        'bid_form': BidForm(),
        'comments': auction.get_comments.all(),
        'comment_form':CommentForm(),
        'title':'Auction',
        'order':order,
    })

@login_required
def bid(request, auction_id):

    if request.user.is_authenticated: 
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False) 
        items = order.orderitem_set.all() 
        cartItems = order.get_cart_items
    else: 
        items = [] 
        order = {'get_cart_total':0 , 'get_cart_items':0}
        cartItems = order['get_cart_items']

    #allows users to bid

    auction = Auction.objects.get(id=auction_id)
    amount = Decimal(request.POST['amount'])

    if amount >= auction.starting_bid and (auction.current_bid is None or amount > auction.current_bid):
        auction.current_bid = amount
        form = BidForm(request.POST)
        new_bid = form.save(commit=False)
        new_bid.auction = auction
        new_bid.auction = auction
        new_bid.user = request.user
        new_bid.save()
        auction.save()

        return HttpResponseRedirect(reverse('auction_detail',args=[auction_id]))

    else:
        return render (request, 'auction.html', {
            'categories':Category.objects.all(),
            'auction':auction,
            'images':auction.get_images.all(),
            'form':BidForm(),
            'error_min_value':True,
            'title':'Auction',
            'order':order,
        })

def auction_close(request, auction_id):

    # allows user to close bid declaring the highest bidder winner
    # makes listing no longer active
    auction = Auction.objects.get(id=auction_id)

    if request.user == auction.creator:
        auction.active = False
        auction.buyer = Bid.objects.filter(auction=auction).last().user
        auction.save()

        return HttpResponseRedirect(reverse('auction_detail', args=[auction_id]))

    else:
        auction.watchers.add(request.user)

        return HttpResponseRedirect(reverse('watchlist'))

def comment(request, auction_id):
    #allows users to add comment 

    if request.user.is_authenticated: 
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False) 
        items = order.orderitem_set.all() 
        cartItems = order.get_cart_items
    else: 
        items = [] 
        order = {'get_cart_total':0 , 'get_cart_items':0}
        cartItems = order['get_cart_items']

    auction = Auction.objects.get(id=auction_id)
    form = CommentForm(request.POST)
    new_comment = form.save(commit=False)
    new_comment.user = request.user
    new_comment.auction = auction
    new_comment.save()

    return HttpResponseRedirect(reverse('auction_detail', args=[auction_id]))

def category_detail(request, category_name):
    #displays products of the same category

    if request.user.is_authenticated: 
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False) 
        items = order.orderitem_set.all() 
        cartItems = order.get_cart_items
    else: 
        items = [] 
        order = {'get_cart_total':0 , 'get_cart_items':0}
        cartItems = order['get_cart_items']

    category = Category.objects.get(category_name=category_name)
    auctions = Auction.objects.filter(category=category)

    for auction in auctions:
        auction.image = auction.get_images.first()

    page = request.GET.get('page', 1)
    paginator = Paginator(auctions, 3)
    try:
        pages = paginator.page(page)
    except PageNotAnInteger:
        pages = paginator.page(1)
    except EmptyPage:
        pages = paginator.page(paginator.num_pages)

    return render (request, 'category.html', {
        'categories':Category.objects.all(),
        'auctions':auctions,
        'auctions_count':auctions.count(),
        'pages':pages,
        'title':category.category_name
    })

def buy(request):

    if request.user.is_authenticated: 
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False) 
        items = order.orderitem_set.all() 
        cartItems = order.get_cart_items
    else: 
        items = [] 
        order = {'get_cart_total':0 , 'get_cart_items':0}
        cartItems = order['get_cart_items']

    
    products = Product.objects.all()
    context = {'products':products, "order":order,'categories': Category.objects.all(),}
    return render(request,'buy.html',context)


def cart(request): 
    if request.user.is_authenticated: 
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False) 
        items = order.orderitem_set.all() 
        cartItems = order.get_cart_items
    else: 
        items = [] 
        order = {'get_cart_total':0 , 'get_cart_items':0}
        cartItems = order['get_cart_items']
        
    context = {'items':items,'order':order,'cartItems':cartItems , 'shipping':False,'categories': Category.objects.all(),} 
    return render(request,'cart.html',context)

def checkout(request): 
    if request.user.is_authenticated: 
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False) 
        items = order.orderitem_set.all() 
        cartItems = order.get_cart_items
    else: 
        items = [] 
        order = {'get_cart_total':0 , 'get_cart_items':0}
        cartItems = order['get_cart_items']
    context = {'items':items,'order':order,'cartItems':cartItems , 'shipping':False,'categories': Category.objects.all(),} 
    return render(request,'checkout.html',context)

def updateItem(request):
	data = json.loads(request.body)
	productId = data['productId']
	action = data['action']
	print('Action:', action)
	print('Product:', productId)

	customer = request.user
	product = Product.objects.get(id=productId)
	order, created = Order.objects.get_or_create(customer=customer, complete=False)

	orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

	if action == 'add':
		if (product.quantity > orderItem.quantity): orderItem.quantity = (orderItem.quantity + 1);product.quantity = (product.quantity - 1)
	elif action == 'remove':
		orderItem.quantity = (orderItem.quantity - 1);product.quantity = (product.quantity + 1)

	orderItem.save()

	if orderItem.quantity <= 0:
		orderItem.delete()
    


	return JsonResponse('Item was added', safe=False)
	
def processorder(request):
	transaction_id = datetime.datetime.now().timestamp()
	data = json.loads(request.body)
	if request.user.is_authenticated:
		customer = request.user
		order, created = Order.objects.get_or_create(customer=customer, complete=False)
	else:
		print('User Not logged In')

	total = float(data['form']['total'])
	order.transaction_id = transaction_id;

	if total == order.get_cart_total:
		order.complete = True;
	order.save()

	if order.shipping == True:
		ShippingAddress.objects.create(
		customer=customer,
		order=order,
		address=data['shipping']['address'],
		city=data['shipping']['city'],
		state=data['shipping']['state'],
		zipcode=data['shipping']['zipcode'],
		)
                
    

	return JsonResponse('Payment submitted..', safe=False)



@login_required
def additem(request):
    # ImageInvFormSet = forms.modelformset_factory(ImageInventory, form = ImageForm)
    if request.method == 'POST':
        product_form = productForm(request.POST, request.FILES)
        # image_form = ImageInvFormSet(request.POST, request.FILES, queryset=ImageInventory.objects.none())

        if product_form.is_valid():
            new_inventory = product_form.save(commit=False)
            new_inventory.creator = request.user
            new_inventory.save()


            return render(request, 'additems.html', {
                'categories': Category.objects.all(),
                'product_form':productForm(),
                'title': 'Add New Item in Inventory',
                'success': True
            })

        else:
            return render(request, 'additems.html', {
                'categories':Category.objects.all(),
                'product_form': productForm(),
                # 'image_form':ImageInvFormSet(queryset=ImageInventory.objects.none()),
                'title':'Add New Item in Inventory'
            })
    else:
        return render(request, 'additems.html', {
                'categories':Category.objects.all(),
                'product_form': productForm(),
                'title':'Add New Item in Inventory'
            })
    


def products_detail(request, product_id):

    #displays the content of an auction

    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse('login'))

    product = Product.objects.get(id=product_id)

    if request.user in product.Invwatchers.all():
        product.is_watched = True

    else: 
        product.is_watched = False

    return render(request, 'buying_products.html', {
        'categories': Category.objects.all(),
        'product':product,
        # 'images':product.get_inventory_images.all(),
        # 'comments': product.get_inventory_comments.all(),
        # 'comment_form':CommentForm(),
        'title':'Inventory'
    })

