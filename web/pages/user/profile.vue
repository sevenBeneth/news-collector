<template>
	<view class="container">
		<view class="content">
			<view class="list">
				<view class="item photo-item">
					<view class="name">头像</view>
					<view class="value">
						<image v-if="user.avatar_url" :src="user.avatar_url" mode="aspectFill"></image>
						<image v-else src="/static/images/default_user_photo.jpg" mode="aspectFill"></image>
					</view>
				</view>
				<view class="item">
					<view class="name">昵称</view>
					<view class="value">{{ user.nickname }}</view>
				</view>
				<view class="item">
					<view class="name">手机号码</view>
					<view class="value">{{ user.mobile }}</view>
				</view>
				<view class="item">
					<view class="name">注册状态</view>
					<view class="value">{{ statusText }}</view>
				</view>
				<navigator class="item" url="password" hover-class="none">
					<view class="name">修改密码</view>
					<text class="value"></text>
					<view class="go"><iconfont type="go"></iconfont></view>
				</navigator>
			</view>
			<view class="submit">
				<view class="btn-text" @tap="logout()">退出登录</view>
			</view>
		</view>
		<pageLoading v-if="showPageLoading"></pageLoading>
	</view>
</template>

<script>
import pageLoading from '@/components/loading/pageLoading.vue';
import iconfont from '@/components/iconfont/iconfont.vue';
export default {
	components: {
		pageLoading,
		iconfont
	},
	data() {
		return {
			user: {},
			showPageLoading: true
		};
	},
	onShow() {
		this.$initPageTitle(); //初始化页面标题
		let source = uni.getStorageSync('source');
		if (source == 'login') {
			uni.removeStorageSync('source');
			// #ifdef H5
			uni.navigateTo({
				url: '/pages/user/index'
			});
			// #endif

			// #ifndef H5
			uni.switchTab({
				url: '/pages/user/index'
			});
			// #endif
		}
	},
	onLoad(e) {
		this.loadData();
	},
	computed: {
		/*注册状态（status = 1 表示账号正常）*/
		statusText() {
			if (!this.user.id) {
				return '--';
			}
			return this.user.status == 1 ? '正常' : '已禁用';
		}
	},
	onPullDownRefresh() {
		uni.showLoading({
			title: '刷新中'
		});
		this.loadData();
	},
	methods: {
		/*加载数据*/
		loadData() {
			this.getData();
		},

		/*获取数据*/
		getData() {
			this.$app.request({
				url: this.$api.user.userInfo,
				data: {},
				method: 'POST',
				dataType: 'json',
				success: res => {
					if (res.code == 0) {
						this.user = res.data;
						this.showPageLoading = false;
					} else {
						this.$alert(res.msg);
					}
				},
				complete: res => {
					uni.stopPullDownRefresh();
					uni.hideLoading();
				}
			});
		},

		/*退出登录*/
		logout() {
			uni.showModal({
				title: '提示',
				content: '确认退出登录？',
				confirmText: '是',
				cancelText: '否',
				success: result => {
					if (result.confirm) {
						this.$app.request({
							url: this.$api.user.logout,
							method: 'POST',
							success: res => {
								if (res.code == 0) {
									uni.removeStorageSync('isLogin');
									uni.removeStorageSync('accessToken');
									uni.removeStorageSync('currentUser');
									uni.removeStorageSync('platform');
									uni.setStorageSync('source', 'logout');
									// #ifdef H5
									this.$alert('退出登录成功', 'success', '/pages/user/index');
									// #endif
									// #ifndef H5
									this.$alert('退出登录成功', 'success', '/pages/user/index', 'switchTab');
									// #endif
								} else {
									this.$alert(res.msg, 'warning');
								}
							},
							complete: function() {
								uni.hideLoading();
							}
						});
					}
				}
			});
		}
	}
};
</script>

<style lang="scss" scoped>
.list {
	margin-top: 2rpx;
	padding-left: 24rpx;
	padding-right: 24rpx;
	border-bottom: 1rpx solid #eee;
	background: #fff;
	.item {
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: space-between;
		min-height: 76rpx;
		border-top: 1rpx solid #eee;
		padding: 10rpx 0;
		&:first-child {
			border: 0;
		}
		.name {
			flex-grow: 0;
			flex-shrink: 0;
			display: flex;
			flex-direction: row;
			align-items: center;
			font-size: 30rpx;
			width: 200rpx;
			color: #555;
			::v-deep .icon {
				color: #0b88ff;
				margin-right: 10rpx;
			}
			::v-deep .icon-mobile-01 {
				font-size: 38rpx;
				margin-right: 5rpx;
				margin-left: -5rpx;
			}
			::v-deep .icon-policy-file {
				font-size: 30rpx;
				margin-right: 14rpx;
				margin-left: -2rpx;
				margin-top: 2rpx;
			}
			text {
				color: #555;
			}
		}
		.value {
			flex-grow: 1;
			flex-shrink: 1;
			display: flex;
			flex-direction: row;
			align-items: center;
			font-size: 30rpx;
			width: 100%;
			justify-content: flex-start;
			text-align: left;
			::v-deep.icon {
				margin-left: 20rpx;
				font-size: 20rpx;
				color: #c1c4c9;
			}
			input {
				padding-right: 30rpx;
				font-size: 30rpx;
				width: 100%;
			}
			image {
				width: 60rpx;
				height: 60rpx;
				border-radius: 50%;
				margin-right: 10rpx;
			}
			text {
				margin-right: 15rpx;
				text-align: left;
				line-height: normal;
				padding: 10rpx 0 10rpx 0;
			}
			.nickname {
				font-size: 30rpx;
			}
		}
		.go {
			display: flex;
			flex-direction: row;
			align-items: center;
			justify-content: center;

			::v-deep.icon {
				color: #dddddd;
				font-size: 20rpx;
			}
		}
		.location {
			display: flex;
			flex-direction: row;
			align-items: center;
			justify-content: center;
			::v-deep.icon {
				color: grey;
			}
		}
		.drive-type {
			display: flex;
			align-items: center;
			.check-item {
				display: flex;
				align-items: center;
				margin-left: 30rpx;
				&:first-child {
					margin-left: 0;
				}
				.check-name {
					font-size: 30rpx;
					line-height: normal;
				}
			}
		}
	}
	.photo-item {
		height: 150rpx;
		image {
			width: 120rpx;
			height: 120rpx;
			border-radius: 50%;
		}
	}
	.textarea-item {
		padding-top: 10rpx;
		height: 110rpx;
		align-items: flex-start;
		.name {
			padding-top: 10rpx;
		}
		.value {
			textarea {
				padding-top: 12rpx;
				height: 100rpx;
				font-size: 30rpx;
				word-wrap: break-word;
				width: 524rpx;
				line-height: 1.5;
			}
		}
	}
}
.submit {
	padding: 30rpx 0 70rpx;
	background: #fff;
	.btn-text {
		display: flex;
		justify-content: center;
		margin-top: 24rpx;
		font-size: 32rpx;
		color: #ffd100;
	}
}
</style>
