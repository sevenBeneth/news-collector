<template>
	<view class="keyword-tags" v-if="tagList.length > 0">
		<view class="keyword-tags__item" :class="['keyword-tags__item--' + size, { 'is-anim': animated }]"
			:style="animated ? ('animation-delay:' + (index * 70) + 'ms') : ''"
			v-for="(item, index) in tagList" :key="index">
			{{ item }}
		</view>
	</view>
</template>

<script>
export default {
	name: 'keyword-tags',
	props: {
		// 关键词，支持逗号（中英文）、分号、顿号分隔的字符串，或字符串数组
		keywords: {
			type: [String, Array],
			default: ''
		},
		// 尺寸：normal / small
		size: {
			type: String,
			default: 'normal'
		},
		// 是否逐个渐入（AI 摘要卡片生成完成时使用）
		animated: {
			type: Boolean,
			default: false
		}
	},
	computed: {
		/*拆分关键词，去空、去重*/
		tagList() {
			let keywords = this.keywords;
			if (!keywords) {
				return [];
			}
			if (typeof keywords === 'string') {
				keywords = keywords.split(/[,，;；、|]/);
			}
			if (!(keywords instanceof Array)) {
				return [];
			}
			let list = [];
			keywords.forEach(item => {
				if (item === null || item === undefined) {
					return;
				}
				let text = String(item).trim();
				if (text && list.indexOf(text) == -1) {
					list.push(text);
				}
			});
			return list;
		}
	}
};
</script>

<style lang="scss">
@keyframes kwSlideUp {
	from { opacity: 0; transform: translateY(10rpx) scale(0.96); }
	to { opacity: 1; transform: translateY(0) scale(1); }
}

.keyword-tags {
	display: flex;
	flex-direction: row;
	flex-wrap: wrap;
	align-items: center;

	&__item {
		margin: 12rpx 12rpx 0 0;
		border-radius: 24rpx;
		color: #c62828;
		background: rgba(198, 40, 40, 0.08);
		white-space: nowrap;

		/* 逐个渐入：动画延迟由父组件传入 */
		&.is-anim {
			opacity: 0;
			animation: kwSlideUp 0.34s ease-out both;
		}

		&--normal {
			padding: 6rpx 20rpx;
			font-size: 26rpx;
			line-height: 1.4;
		}

		&--small {
			padding: 4rpx 16rpx;
			font-size: 22rpx;
			line-height: 1.4;
		}
	}
}
</style>
