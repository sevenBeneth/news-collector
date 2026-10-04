<template>
	<view class="ai-summary-card" v-if="summary">
		<view class="ai-summary-card__header">
			<!-- AI 徽标 -->
			<view class="ai-summary-card__badge">AI 摘要</view>
			<text class="ai-summary-card__model" v-if="model">{{ model }}</text>
		</view>
		<!-- 摘要正文 -->
		<view class="ai-summary-card__body">{{ summary }}</view>
		<!-- 关键词标签 -->
		<keyword-tags v-if="keywords" :keywords="keywords" size="small" />
		<!-- 必须保留的 AI 免责提示 -->
		<view class="ai-summary-card__tip">内容由 AI 生成，仅供参考</view>
	</view>
</template>

<script>
import keywordTags from '@/components/keyword-tags/keyword-tags.vue';
export default {
	name: 'ai-summary-card',
	components: {
		keywordTags
	},
	props: {
		// 摘要文本，为空时整个卡片不渲染
		summary: {
			type: String,
			default: ''
		},
		// 关键词，逗号分隔字符串（也兼容数组）
		keywords: {
			type: [String, Array],
			default: ''
		},
		// 生成摘要的模型名，可选
		model: {
			type: String,
			default: ''
		}
	}
};
</script>

<style lang="scss">
.ai-summary-card {
	padding: 24rpx;
	border-radius: 16rpx;
	background: rgba(198, 40, 40, 0.06);
	border-left: 6rpx solid #c62828;

	&__header {
		display: flex;
		flex-direction: row;
		align-items: center;
	}

	/*AI 徽标*/
	&__badge {
		padding: 4rpx 16rpx;
		border-radius: 6rpx;
		color: #ffffff;
		background: #c62828;
		font-size: 22rpx;
		font-weight: bold;
		line-height: 1.6;
		letter-spacing: 2rpx;
	}

	&__model {
		margin-left: 12rpx;
		color: #c62828;
		opacity: 0.7;
		font-size: 22rpx;
		line-height: normal;
	}

	&__body {
		margin-top: 16rpx;
		color: #444444;
		font-size: 28rpx;
		line-height: 1.6;
		text-align: justify;
	}

	/*AI 生成提示*/
	&__tip {
		margin-top: 16rpx;
		color: #999999;
		font-size: 22rpx;
		line-height: normal;
	}
}
</style>
