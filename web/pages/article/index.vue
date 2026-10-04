<template>
	<view class="page">
		<view class="status-bar"></view>
		<view class="top">
			<!-- #ifdef MP -->
			<!-- 页面标题 -->
			<view class="page-title" :style="'height: ' + navBarHeight">
				<image src="../../static/images/logo.png"></image>
			</view>
			<!-- 搜索 -->
			<view class="search" :style="showNavFloat ? 'display:none' : ''">
				<navigator class="input" :url="'search?category_id=' + category_id" hover-class="none">
					<iconfont type="search"></iconfont>
					<text>输入关键字</text>
				</navigator>
			</view>
			<!-- #endif -->

			<!-- 搜索 -->
			<!-- #ifdef H5 -->
			<view class="search">
				<image class="logo" mode="aspectFit" src="../../static/images/logo.png"></image>
				<navigator class="input" :url="'search?category_id=' + category_id" hover-class="none">
					<iconfont type="search"></iconfont>
					<text>输入关键字</text>
				</navigator>
				<navigator class="user" url="/pages/user/index" hover-class="none">
					<iconfont type="user-01"></iconfont>
					<!-- <image v-if="current.user" :src="user.avatar_url"></image> -->
					<!-- <image src="/static/images/default_user_photo.jpg" @tap="login()"></image> -->
				</navigator>
			</view>
			<!-- #endif -->

			<!-- 导航 -->
			<view class="navbar" :class="showNavFloat ? 'floatbar' : ''">
				<view class="menu" v-if="category.length > 0">
					<view class="category">
						<scroll-view :scroll-x="true" :scroll-with-animation="true" :scroll-into-view="scroll_category_id" @scroll="navFloatShow()">
							<view class="item" v-for="(item, index) in category" :key="index" :class="category_id == item.id ? 'current' : ''"
							 :id="'category_id-' + index" :style="'width:' + (category.length <= 4 ? 100 / category.length + '%' : '')" @tap="categoryChange(item.id, index)">
								<view class="text">
									<text>{{ item.name }}</text>
									<!-- <image src="/static/images/bg_tab.png"></image> -->
								</view>
							</view>
						</scroll-view>
					</view>
					<view class="list" @tap="menuShow(!showMenu)">
						<iconfont type="menu-01"></iconfont>
					</view>
				</view>
			</view>
		</view>
		<view class="content">
			<view class="menu-block fade-in" v-show="showMenu">
				<view class="list">
					<text class="item" v-for="(item, index) in category" :key="index" :class="category_id == item.id ? 'current' : ''"
					 :id="'category_id-' + (index + 1)" @tap="categoryChange(item.id, index)">
						{{ item.name }}
					</text>
				</view>
			</view>
			<scroller @init="initScroller" @down="refreshData" @up="getData" :up="optUp" @scroll="navFloatShow(scroller)" :fixed="false">
				<!-- 轮播图（数据来自 /api/banner） -->
				<bannerSwiper :list="banner" height="320rpx" @click="bannerClick" />
				<!-- 新闻列表 -->
				<view class="list" v-if="list.length > 0">
					<navigator :url="'/pages/article/detail?id=' + item.id" class="item" v-for="(item, index) in list" :key="index" hover-class="none">
						<view class="info">
							<view class="text">
								<view class="title">{{ item.title }}</view>
								<!-- AI 摘要前 40 字 -->
								<view class="ai-summary" v-if="item.ai_summary">{{ summaryText(item.ai_summary) }}</view>
								<view class="other">
									<view class="left">
										<view class="source" v-if="item.origin">{{ item.origin }}</view>
										<view class="time">{{ item.publish_time }}</view>
									</view>
									<view class="right" v-if="item.comment_count > 0">
										<image src="/static/images/icon_comment.png"></image>
										<text>{{ item.comment_count }}</text>
									</view>
									<view class="right view" v-else>
										<image src="/static/images/icon_view.png"></image>
										<text>{{ item.read_count }}</text>
									</view>
								</view>
							</view>
							<view class="photo"><image :src="item.photo_url" mode="aspectFill"></image></view>
						</view>
						<view class="line"></view>
					</navigator>
				</view>
			</scroller>
		</view>
		<pageLoading v-if="showPageLoading"></pageLoading>
	</view>
</template>

<script>
	import scroller from '@/components/scroller/scroller.vue';
	import bannerSwiper from '@/components/banner-swiper/banner-swiper.vue';
	import pageLoading from '@/components/loading/pageLoading.vue';
	import iconfont from '@/components/iconfont/iconfont.vue';
	import util from '@/common/util.js';
	export default {
		components: {
			bannerSwiper,
			pageLoading,
			scroller,
			iconfont
		},
		data() {
			return {
				scroller: {},
				optUp: {
					auto: true,
					onScroll: true,
					page: {
						size: 20
					},
					empty: {
						tip: '暂无数据~'
					}
				},
				category_id: 1,
				category_index: 0,
				scroll_category_id: 'scroll_category_id_0',
				category: [],
				showMenu: false,
				banner: [],
				list: [],
				showNoData: false,
				showPageLoading: true,
				showNavFloat: false,
				navBarHeight: ''
			};
		},
		onShow() {
			this.$initPageTitle(); //初始化页面标题
			console.log('onShow')
			/*导航栏高度*/
			if (this.navBarHeight == '') {
				this.navBarHeight = this.$app.getNaviBarHeight();
			}
			uni.removeStorageSync('cancelLogin');
			/*来源是登录时更新*/
			let source = uni.getStorageSync('source');
			if (source == 'login') {
				uni.removeStorageSync('source');
				this.loadData();
			}
		},
		onShareAppMessage() {
			return {
				path: '/pages/article/index',
				success: function(e) {},
				title: '团节社成都'
			};
		},
		onLoad(e) {
			// #ifdef H5
			if (e.category_id > 0) {
				this.category_id = e.category_id;
			}
			if (e.category_index > 0) {
				this.category_index = e.category_index;
			}
			// #endif
			this.getCategory();
			this.getBanner(); //获取首页轮播
		},
		onPullDownRefresh() {
			uni.showLoading({
				title: '刷新中'
			});
			this.loadData();
		},
		methods: {
			/*初始化滚动*/
			initScroller(scroller) {
				this.scroller = scroller;
			},

			/*刷新数据*/
			refreshData() {
				uni.showLoading({
					title: '刷新中'
				});
				this.getBanner(); //刷新轮播
				this.scroller.resetUpScroll();
			},

			/*加载数据*/
			loadData() {
				this.list = [];
				this.scroller.resetUpScroll();
			},

			/*获取子类别数据*/
			getCategory() {
				this.$app.request({
					url: this.$api.article.category,
					method: 'POST',
					dataType: 'json',
					success: res => {
						if (res.code == 0) {
							this.category = res.data;
							if (this.category_index > -1) {
								let nextIndex = this.category_index - 1;
								nextIndex = nextIndex <= 0 ? 0 : nextIndex;
								this.scroll_category_id = `category_id-${nextIndex}`; //动画滚动,滚动至中心位置
							}
						} else {
							this.$alert(res.msg);
						}
					},
					complete: res => {}
				});
			},

			/*获取轮播数据*/
			getBanner() {
				this.$app.request({
					url: this.$api.banner,
					method: 'POST',
					dataType: 'json',
					success: res => {
						if (res.code == 0 && res.data) {
							this.banner = res.data;
						}
					}
				});
			},

			/*获取数据*/
			getData() {
				this.$app.request({
					url: this.$api.article.index,
					data: {
						category_id: this.category_id,
						page_index: this.scroller.num,
						page_size: this.scroller.size,
					},
					method: 'POST',
					dataType: 'json',
					success: res => {
						if (res.code == 0) {
							if (this.scroller.num == 1) {
								this.list = [];
							}
							if (this.banner.length == 0 && res.data.slider) {
								this.banner = res.data.slider; //banner 接口为空时兜底使用列表接口的 slider
							}
							this.list = this.list.concat(res.data.list);
							this.scroller.endByPage(res.data.list.length, res.data.page);
							this.showPageLoading = false;
						} else {
							this.scroller.endSuccess();
							this.$alert(res.msg);
						}
					},
					fail: res => {
						this.scroller.endErr();
					},
					complete: res => {
						uni.stopPullDownRefresh();
						uni.hideLoading();
					}
				});
			},

			/*切换导航*/
			categoryChange(category_id, index) {
				this.showMenu = false;
				this.category_index = index;
				this.category_id = category_id;
				var nextIndex = index - 1;
				nextIndex = nextIndex <= 0 ? 0 : nextIndex;
				this.scroll_category_id = `category_id-${nextIndex}`; //动画滚动,滚动至中心位置
				this.loadData();

				// #ifdef H5
				// uni.navigateTo({
				// 	url: '/pages/article/list?category_id=' + this.category_id + '&category_index=' + this.category_index
				// });
				// #endif
			},

			/*轮播点击：有关联新闻跳详情，否则打开外链*/
			bannerClick(item) {
				if (!item) {
					return;
				}
				if (item.news_id > 0) {
					uni.navigateTo({
						url: '/pages/article/detail?id=' + item.news_id
					});
					return;
				}
				if (item.link_url) {
					// #ifdef H5
					window.open(item.link_url);
					// #endif
					// #ifndef H5
					uni.setClipboardData({
						data: item.link_url,
						success: res => {
							this.$alert('链接已复制', 'success');
						}
					});
					// #endif
				}
			},

			/*截取 AI 摘要前 40 字*/
			summaryText(text) {
				if (!text) {
					return '';
				}
				text = String(text);
				if (text.length > 40) {
					return text.substr(0, 40) + '...';
				}
				return text;
			},

			/*滚动时导航栏浮动*/
			navFloatShow(scroller) {
				if (scroller) {
					if (scroller.scrollTop > 60) {
						if (!this.showNavFloat) {
							this.showNavFloat = true;
						}
					} else {
						if (this.showNavFloat) {
							this.showNavFloat = false;
						}
					}
				}
			},
			/*菜单框展示*/
			menuShow(value) {
				this.showMenu = value;
			},
			/*隐藏导航浮动*/
			navFloatHide() {
				this.showNavFloat = false;
			}
		}
	};
</script>

<style scoped lang="scss">
	page {
		height: 100%;
	}

	.page {
		display: flex;
		flex: 1;
		flex-direction: column;
		overflow: hidden;
		height: 100%;
	}

	.content {
		flex: 1;
		width: 100%;
		height: 100rpx;
	}

	/*头部*/
	.top {

		/*页面标题*/
		.page-title {
			display: flex;
			justify-content: center;
			align-items: center;
			height: 90rpx;
			text-align: center;
			border-bottom: 1rpx solid #efefef;
			z-index: 9999;
			line-height: 1;

			image {
				height: 50rpx;
				width: 280rpx;
				margin-left: -35rpx;
			}
		}

		/*搜索*/
		.search {
			padding: 24rpx 24rpx 0 24rpx;
			display: flex;
			justify-content: space-between;
			align-items: center;

			.logo {
				height: 60rpx;
				width: 474rpx;
				margin-right: 30rpx;
			}

			.input {
				margin-left: 0 !important;
				display: flex;
				align-items: center;
				height: 70rpx;
				width: 100%;
				background: #f5f5f5;
				border-radius: 34rpx 34rpx 0 34rpx;

				::v-deep .icon {
					margin-left: 28rpx;
					color: #aaaaaa;
					font-size: 32rpx;
					line-height: 1;
				}

				text {
					margin-left: 14rpx;
					font-size: 30rpx;
					color: #aaaaaa;
					line-height: 1;
				}
			}

			.user {
				display: flex;
				align-items: center;

				::v-deep .icon {
					margin-left: 24rpx;
					color: #aaaaaa;
					font-size: 38rpx;
					margin-top: 4rpx;
				}

				image {
					width: 50rpx;
					height: 50rpx;
					border-radius: 50%;
					margin-left: 25rpx;
				}
			}
		}

		/* 顶部navbar */
		.navbar {

			/*分类*/
			.menu {
				position: relative;
				height: 80rpx;
				white-space: nowrap;
				padding: 15rpx 0 6rpx;
				z-index: 10;
				display: flex;
				align-items: center;
				justify-content: space-between;

				/*分类*/
				.category {
					width: 650rpx;
					margin-left: 30rpx;
					white-space: nowrap;
					position: relative;

					scroll-view {
						width: auto;

						.item {
							position: relative;
							display: inline-block;
							margin: 0 20rpx 0;
							height: 80rpx;
							text-align: left;
							padding-top: 7rpx;

							//line-height: 80rpx;
							&:first-child {
								margin-left: 10rpx;
							}

							&:after {
								content: '';
								width: 0;
								height: 0;
								position: absolute;
								left: 50%;
								bottom: 0;
								transform: translateX(-50%);
								transition: 0.3s;
							}

							.text {
								position: relative;
								width: auto;
								height: auto;
								line-height: auto;
								display: inline-block;

								text {
									font-size: 36rpx;
									font-weight: bold;
									color: #555;
								}

								image {
									position: absolute;
									top: 16rpx;
									right: -14rpx;
									width: 50rpx;
									height: 50rpx;
									display: none;
								}
							}
						}

						.current {
							&:after {
								width: 50%;
							}

							.text {
								text {
									font-size: 40rpx;
									font-weight: bold;
									color: #262626;
								}

								image {
									display: block;
								}

								border-bottom: 6rpx solid #ffd100;
							}
						}
					}
				}

				.list {
					width: 70rpx;
					display: flex;
					align-items: center;
					justify-content: center;

					//box-shadow: -4rpx 0 0 #e9ebee;
					//box-shadow: -2px 0 0 #262626;
					::v-deep .icon {
						font-size: 36rpx;
						margin-top: -6rpx;
					}
				}
			}
		}
	}

	.menu-block {
		position: absolute;
		top: 0;
		left: 0;
		background: #fff;
		border-bottom: 1rpx solid #f5f5f5;
		padding: 20rpx 0 50rpx;
		z-index: 100;
		width: 100%;

		//box-shadow: 0 15rpx 10rpx -15rpx #e9ebee;
		.list {
			padding-left: 10rpx;

			text {
				background: #f5f7fa;
				border-radius: 8rpx;
				font-size: 32rpx;
				margin: 12rpx 20rpx;
				display: inline-block;
				height: 72rpx;
				width: 144rpx;
				line-height: 72rpx;
				text-align: center;
			}

			.current {
				color: #fff;
				background: #ffd100;
				//font-size: 32rpx;
			}
		}
	}

	.scroll {
		height: 100%;
	}

	/*文章列表*/
	.list {
		margin-top: 2rpx;

		.item {
			padding: 40rpx 24rpx 0 24rpx;

			.info {
				display: flex;
				flex-direction: row;
				justify-content: space-between;
				padding-bottom: 4rpx;

				.text {
					flex-grow: 1;
					flex-shrink: 1;
					display: flex;
					flex-direction: column;
					margin-right: 40rpx;

					.title {
						flex-grow: 1;
						flex-shrink: 1;
						font-size: 30rpx;
						line-height: 1.2;
						display: -webkit-box;
						text-overflow: ellipsis;
						word-break: break-all;
						-webkit-line-clamp: 2;
						-webkit-box-orient: vertical;
						overflow: hidden;
						margin-bottom: 8rpx;
					}

					/*AI 摘要前 40 字*/
					.ai-summary {
						margin-bottom: 8rpx;
						color: #888888;
						font-size: 26rpx;
						line-height: 1.4;
						text-overflow: ellipsis;
						white-space: nowrap;
						overflow: hidden;
					}

					.other {
						flex-grow: 1;
						flex-shrink: 1;
						display: flex;
						align-items: center;
						font-size: 28rpx;
						color: #999;
						line-height: normal;

						.left {
							display: flex;
							flex-grow: 1;
							flex-shrink: 1;

							.source {
								display: -webkit-box;
								text-overflow: ellipsis;
								word-break: break-all;
								-webkit-line-clamp: 1;
								-webkit-box-orient: vertical;
								overflow: hidden;
								width: 140rpx;
								margin-right: 16rpx;
							}
						}

						.right {
							display: flex;
							flex-direction: row;
							justify-content: center;
							align-items: center;
							flex-grow: 0;
							flex-shrink: 0;
							margin-right: 5rpx;

							image {
								flex-grow: 1;
								flex-shrink: 1;
								width: 28rpx;
								height: 28rpx;
								margin-right: 12rpx;
							}

							text {
								flex-grow: 1;
								flex-shrink: 1;
								margin-top: -6rpx;
							}
						}

						.view {
							image {
								width: 40rpx;
								height: 40rpx;
								margin-right: 5rpx;
							}
						}
					}
				}

				.photo {
					image {
						height: 170rpx;
						width: 222rpx;
						border-radius: 10rpx;
					}
				}
			}

			.line {
				width: 100%;
				height: 1rpx;
				margin-top: 22rpx;
				background: #e8e8e8;
			}
		}
	}

	/*浮动navbar*/
	.floatbar {
		//border-bottom: 1rpx solid #e8e8e8;
		box-shadow: 0px 2px 2px -2px #e8e8e8;
		padding-bottom: 12rpx;
	}

	::v-deep .no-data {
		margin-top: 200rpx;
	}
</style>
