<template>
	<view class="banner-swiper" v-if="list.length > 0">
		<swiper
			class="banner-swiper__swiper"
			:style="'height:' + height"
			:indicator-dots="false"
			:autoplay="true"
			:interval="4000"
			:duration="400"
			:circular="true"
			@change="swiperChange"
		>
			<swiper-item v-for="(item, index) in list" :key="index">
				<view class="banner-swiper__item" @tap="itemClick(item)">
					<image class="banner-swiper__image" :src="item.image_url" mode="aspectFill"></image>
					<!-- 标题浮层 -->
					<view class="banner-swiper__title" v-if="item.title">
						<text class="banner-swiper__title-text">{{ item.title }}</text>
					</view>
				</view>
			</swiper-item>
		</swiper>
		<!-- 底部小圆点指示器 -->
		<view class="banner-swiper__dots" v-if="list.length > 1">
			<view
				class="banner-swiper__dot"
				:class="current == index ? 'banner-swiper__dot--current' : ''"
				v-for="(item, index) in list"
				:key="index"
			></view>
		</view>
	</view>
</template>

<script>
export default {
	name: 'banner-swiper',
	props: {
		// 轮播数据，元素结构：{id, title, image_url, link_url, news_id}
		list: {
			type: Array,
			default: function() {
				return [];
			}
		},
		// 轮播高度
		height: {
			type: String,
			default: '320rpx'
		}
	},
	data() {
		return {
			current: 0 //当前轮播下标
		};
	},
	methods: {
		/*轮播切换*/
		swiperChange(e) {
			this.current = e.detail.current;
		},

		/*点击轮播，抛出点击事件，由父页面处理跳转*/
		itemClick(item) {
			this.$emit('click', item);
		}
	}
};
</script>

<style lang="scss">
.banner-swiper {
	position: relative;
	margin: 14rpx 24rpx 0;
	overflow: hidden;
	border-radius: 16rpx;
	background: #f5f5f5;

	&__swiper {
		width: 100%;
	}

	&__item {
		position: relative;
		width: 100%;
		height: 100%;
	}

	&__image {
		display: block;
		width: 100%;
		height: 100%;
		border-radius: 16rpx;
	}

	/*标题浮层*/
	&__title {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		padding: 40rpx 24rpx 20rpx;
		background-image: linear-gradient(to top, rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0));

		&-text {
			display: -webkit-box;
			overflow: hidden;
			color: #ffffff;
			font-size: 30rpx;
			font-weight: bold;
			line-height: 1.4;
			word-break: break-all;
			text-overflow: ellipsis;
			-webkit-line-clamp: 2;
			-webkit-box-orient: vertical;
		}
	}

	/*小圆点指示器*/
	&__dots {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 16rpx;
		display: flex;
		flex-direction: row;
		justify-content: center;
		align-items: center;
	}

	&__dot {
		width: 12rpx;
		height: 12rpx;
		margin: 0 8rpx;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.5);

		&--current {
			width: 28rpx;
			border-radius: 6rpx;
			background: #ffffff;
		}
	}
}
</style>
