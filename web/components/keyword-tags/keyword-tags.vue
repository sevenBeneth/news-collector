<template>
	<view class="keyword-tags" v-if="tagList.length > 0">
		<view class="keyword-tags__item" :class="'keyword-tags__item--' + size" v-for="(item, index) in tagList" :key="index">
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
