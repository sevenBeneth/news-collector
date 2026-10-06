<template>
	<view class="page">
		<view class="content">
			<view class="banner">
				<view class="app-name">芜湖市科技创新新闻收集平台</view>
				<view class="app-desc">芜湖本地科技创新资讯聚合 · AI 摘要速读</view>
			</view>

			<view class="ul">
				平台定位
				<view class="li">
					面向芜湖本地的科技创新资讯聚合服务：自动汇集科技政策、创新平台、企业创新、成果转化、人才引育、园区动态、通知公告等公开信息，
					并用大模型为每条资讯生成中文摘要与关键词，帮助科技型企业、高校师生、科研与产业管理人员快速掌握本地科技动态。
				</view>
			</view>

			<view class="ul">
				数据来源
				<view class="li">
					平台内容来自以下公开渠道的自动化采集，并在页面显著位置标注来源与原文链接：
					芜湖市科学技术局（通知公告 / 工作动态 / 科技要闻 / 县区科技）、芜湖市人民政府（新闻中心 / 官方 RSS）、芜湖新闻网（要闻 / 大江资讯）等。
				</view>
			</view>

			<view class="ul">
				AI 摘要说明
				<view class="li">
					每条资讯的摘要与关键词由 DeepSeek 大模型自动生成，用于辅助阅读，
					可能存在理解偏差或信息滞后，请以原文为准。所有摘要均标注“内容由 AI 生成，仅供参考”。
				</view>
			</view>

			<view class="ul">
				主要功能
				<view class="li">
					频道浏览与关键词搜索；AI 摘要速读；收藏与评论互动；一键跳转原文。
					采集到的资讯会先进入待审队列，由管理端审核通过后才会在平台展示。
				</view>
			</view>

			<view class="ul">
				免责声明
				<view class="li">
					本平台为课程作业作品，仅用于学习与技术演示，不用于任何商业用途。
					资讯的著作权归原作者及原发布网站所有，平台仅展示标题、来源、原文链接与自动生成的摘要；
					如权利人认为内容不宜展示，请联系我们，我们将及时删除。
				</view>
			</view>

			<view class="ul">
				技术实现
				<view class="li">
					前端：uni-app（Vue2），可编译 H5 与微信小程序；
					后端：Spring Boot + MyBatis + MySQL；
					采集：Python（requests + BeautifulSoup）多源适配器；
					AI：DeepSeek 大模型 API（结构化摘要与关键词）。
				</view>
			</view>

			<view class="footer">芜湖市科技创新新闻收集平台 · 课程作业演示版本</view>
		</view>
	</view>
</template>

<script>
	import iconfont from '@/components/iconfont/iconfont.vue'
	export default {
		components: {
			iconfont
		},
		data() {
			return {

			}
		},
		onShow() {
			this.$initPageTitle('关于本平台'); //初始化页面标题
		},
		onLoad(e) {

		},
		onPullDownRefresh() {

		}
	}
</script>

<style scoped lang="scss">
	.banner {
		padding: 40upx 40upx 20upx;
		.app-name {
			font-size: 38rpx;
			font-weight: bold;
			color: #c62828;
		}
		.app-desc {
			margin-top: 12rpx;
			font-size: 26rpx;
			color: #888;
		}
	}
	.ul {
		margin: 30upx 40upx 20rpx;
		font-size: 34rpx;
		color: #c62828;
		font-weight: bold;
	}
	.li {
		margin: 20upx 0 30upx;
		font-size: 30rpx;
		line-height: 1.6;
		color: #333;
		font-weight: normal;
	}
	.footer {
		margin: 50upx 40upx 60upx;
		font-size: 24rpx;
		color: #aaa;
		text-align: center;
	}
</style>
