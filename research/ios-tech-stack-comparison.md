# iOS 技术栈对比：SwiftUI vs Flutter vs React Native

## 背景与约束

- **目标**：为食品配料表扫描 App（iOS App Store 上架）选择技术栈。
- **用户画像**：只会 Python，零基础移动开发，个人开发者，无公司。
- **核心功能**：相机扫描配料表 → OCR 文字识别 → 成分评分 → 健康预警 → 结果展示。
- **特殊要求**：老人用户多，必须做好无障碍（VoiceOver、大字体、高对比、易触控）。

## 一句话结论

**推荐 Swift + SwiftUI**。理由：它是 iOS 原生方案，学习路径最单一、相机/文字识别最省事、无障碍支持最省心，对个人开发者快速做出 MVP 最友好。

## 评估维度

### 1. 学习曲线

| 技术栈 | 主要学习内容 | 对 Python 小白友好度 |
|---|---|---|
| **Swift + SwiftUI** | Swift 语言 + SwiftUI 声明式 UI | ★★★★☆ 只需学一套苹果官方技术栈 |
| **Flutter** | Dart 语言 + Widget 思维 + 跨平台概念 | ★★★☆☆ 语言新、Widget 嵌套需适应 |
| **React Native** | JavaScript/TypeScript + React + 原生桥接概念 + Xcode/CocoaPods | ★★☆☆☆ 技术栈最多，配置最繁琐 |

> Swift 虽然是新语言，但 Apple 提供“Develop in Swift”官方教程；Flutter/Dart 的语法接近 Java/C#；React Native 要求同时掌握 JS、React、iOS 原生构建链，对纯 Python 背景负担最重。

### 2. 开发效率

- **Swift + SwiftUI**：Xcode 实时预览（Preview）、声明式 UI，官方提供食品/文档扫描直接可用的 `DataScannerViewController`（VisionKit），几行代码即可开始扫描文字。
- **Flutter**：Hot Reload 很快，跨平台一套代码，但调用 iOS 独有 API 时需要写 Platform Channel 或找插件。
- **React Native**：Hot Reload 也有，但需要配置 Metro、CocoaPods、Xcode 签名，遇到原生问题调试时间长。

### 3. 相机与图像/文字识别

| 技术栈 | 主要方案 | 复杂度 |
|---|---|---|
| **Swift + SwiftUI** | `VisionKit.DataScannerViewController` 原生识别文字和条码，本地运行，无需网络 | 低 |
| **Flutter** | `camera` 插件 + `google_mlkit_text_recognition` 等第三方插件 | 中 |
| **React Native** | `react-native-vision-camera` + Frame Processor 或 ML Kit 插件 | 中高 |

> Apple VisionKit 的 `DataScannerViewController` 是 iOS 16+ 官方组件，提供实时相机扫描、文字高亮、点击对焦、捏合缩放，最适合配料表这种“拍文字”场景。[官方文档](https://developer.apple.com/documentation/visionkit/scanning-data-with-the-camera)

### 4. 无障碍 UI

- **Swift + SwiftUI**：系统控件默认带 VoiceOver 标签，SwiftUI 提供 `accessibilityLabel`、`accessibilityValue`、`accessibilityHint` 等修饰符；Apple 人机界面指南对老人/视障用户有完整建议。
- **Flutter**：通过 `Semantics` widget 和 `semanticLabel` 支持 VoiceOver/TalkBack，但需要显式包裹。
- **React Native**：通过 `accessibilityLabel`、`accessibilityRole` 等属性映射原生无障碍树，但默认裸 `View` 没有语义，需要较多手动标注。

> 对老人用户，SwiftUI 能最快达到系统级无障碍体验。

### 5. 性能

| 测试项（非官方基准，仅供参考） | Flutter | React Native | SwiftUI |
|---|---|---|---|
| 万级列表 FPS | 58 | 43 | 60 |
| 粒子动画延迟 | 12 ms | 28 ms | 8 ms |
| 冷启动时间 | 1.2 s | 1.8 s | 0.9 s |

> 数据来源：[CSDN 评测](https://blog.csdn.net/qq_22409661/article/details/146006110)。扫描配料表场景下三者都够用，但 SwiftUI 原生编译、包体最小、启动最快。

### 6. 是否需要 Mac

**三者都需要 Mac + Xcode 才能构建和提交 iOS 应用。**

- Apple 官方要求 iOS 应用必须在 macOS 上用 Xcode 编译、签名并上传到 App Store Connect。
- Flutter 和 React Native 可以在 Windows/Linux 写代码，但**打包 iOS 仍然需要 Mac**。
- 没有 Mac 的替代方案：租用 Mac 云主机、使用 GitHub Actions 远程构建，但本地真机调试和签名会很麻烦。

### 7. 维护成本

| 技术栈 | 维护成本 | 说明 |
|---|---|---|
| **Swift + SwiftUI** | 低 | Apple 长期支持，新 iOS API 当天可用，工具链统一 |
| **Flutter** | 中 | 引擎和插件更新可能带来破坏性变更，Dart 生态相对单一 |
| **React Native** | 中高 | 版本迭代快，CocoaPods、Metro、原生模块兼容性问题较多 |

### 8. App Store 上架与费用

- **Apple Developer Program**：个人开发者年费 **99 美元**（或等值当地货币），**无需公司**，个人法定姓名会显示为“供应商”。
- 如果以个人身份注册，只需要 Apple ID + 双重认证 + 法定成年年龄。

> 官方说明：[Apple Developer Program 计划注册](https://developer.apple.com/cn/help/account/membership/program-enrollment/)

## 综合对比表

| 维度 | Swift + SwiftUI | Flutter | React Native |
|---|---|---|---|
| 学习曲线 | ★★★★☆ | ★★★☆☆ | ★★☆☆☆ |
| 开发效率 | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| 相机/OCR | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| 无障碍 UI | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| 性能 | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| 是否需要 Mac | 是 | 是 | 是 |
| 维护成本 | 低 | 中 | 中高 |
| 未来跨平台扩展 | 不支持 | 支持 | 支持 |
| 适合人群 | iOS 单一平台、想最快出 MVP | 需要同时做 Android/Web | 已有 React/JS 基础 |

## 推荐方案：Swift + SwiftUI

### 推荐理由

1. **对个人开发者最省脑**：只学 Swift 和 SwiftUI，工具只有 Xcode，不用同时折腾 JS、Metro、CocoaPods、Dart、Flutter engine。
2. **扫描功能开箱即用**：VisionKit 的 `DataScannerViewController` 是苹果官方给相机文字识别做的“现成组件”，比 Flutter/RN 的插件组合更稳定。
3. **老人无障碍最省心**：系统控件自带 VoiceOver，SwiftUI 修饰符简单，容易实现大字体、高对比、明确标签。
4. **性能最好、包体最小**：原生编译，启动快，老 iPhone 也能流畅运行。
5. **维护负担最低**：Apple 会持续更新 SwiftUI，不会因为第三方插件停更而卡住。

### 什么时候再考虑 Flutter

- 如果 6 个月内确定要同时上 Android，Flutter 可以省一套代码。
- 但目前需求明确是 **iOS App Store 上架**，不要为了“以后可能跨平台”提前增加复杂度。

### 什么时候再考虑 React Native

- 如果你已经会 React/JS，RN 是合理选择。
- 但你是 Python 背景，RN 的学习和工具链成本最高，不推荐作为第一门移动技术。

## 风险与应对

| 风险 | 应对措施 |
|---|---|
| 没有 Mac | 必须准备 Mac（二手 Mac mini、MacBook Air 或租用云 Mac），否则无法真机调试和上架 |
| 不会 Swift | 从 Apple 官方教程入门，先用 Xcode 做“Hello World”和简单表单，再集成相机 |
| 只想做 iOS | 接受当前范围，不预做多平台；若以后需要 Android，再评估 Flutter 重构 |
| 99 美元年费 | 个人开发者账号即可，无公司也能注册 |

## 下一步行动

1. 确认已有/可获取 Mac 设备。
2. 用个人 Apple ID 注册 Apple Developer Program（年费 99 美元）。
3. 在 Xcode 中新建 SwiftUI 项目，跑通 `DataScannerViewController` 文字扫描原型。
4. 针对老人用户设计首页：大按钮、大字体、扫描结果用“可以买 / 少吃点 / 不要买”等直白结论。
5. 打开 iPhone 的 VoiceOver 实际测试一遍所有按钮和结果页。

## 参考来源

- [SwiftUI 官方文档](https://developer.apple.com/documentation/swiftui)
- [SwiftUI Accessibility 修饰符](https://developer.apple.com/documentation/swiftui/view-accessibility/)
- [VisionKit：使用相机扫描数据](https://developer.apple.com/documentation/visionkit/scanning-data-with-the-camera)
- [DataScannerViewController 官方文档](https://developer.apple.com/documentation/visionkit/datascannerviewcontroller)
- [Flutter iOS 开发环境设置](https://docs.flutter.dev/platform-integration/ios/setup)
- [Flutter 无障碍文档](https://docs.flutter.dev/ui/accessibility)
- [React Native 环境搭建（中文社区）](https://reactnative.cn/docs/0.81/set-up-your-environment)
- [React Native Accessibility 文档](https://react-native.netlify.app/docs/next/accessibility)
- [Apple Developer Program 计划注册](https://developer.apple.com/cn/help/account/membership/program-enrollment/)
- [Swift vs Flutter vs React Native 跨平台评测（CSDN）](https://blog.csdn.net/qq_22409661/article/details/146006110)

## 变更日志

- **v0.15.3 - 2026-07-23**：新增 `research/ios-tech-stack-comparison.md`，对比 SwiftUI / Flutter / React Native，结论推荐 Swift + SwiftUI。
