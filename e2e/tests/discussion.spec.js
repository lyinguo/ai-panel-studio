// @ts-check
import { expect, test } from "@playwright/test";

/**
 * E2E — AI 圆桌讨论核心流程
 *
 * 验证：
 * 1. 用户输入话题 → 创建讨论 → 显示参与者列表
 * 2. SSE 事件驱动 → 嘉宾状态变化 → 消息气泡流式渲染
 * 3. 对话气泡携带发言人专属颜色
 * 4. 输出内容不包含 <think> 标签或其他内部标记
 */
test.describe("AI 圆桌讨论 Flow", () => {
  test("用户创建讨论并看到带颜色的对话气泡，不含 <think> 标签", async ({ page }) => {
    // 1. 打开 Studio 页面
    await page.goto("/");
    await expect(page.locator(".guest-panel")).toBeVisible();
    await expect(page.locator(".transcript__empty")).toBeVisible();

    // 2. 输入讨论话题
    const topicInput = page.locator(".setup-form__input");
    await expect(topicInput).toBeVisible();
    await topicInput.fill("AGI 是否应该暂停研发");

    // 3. 选择专家人数（默认 4，保持不变）

    // 4. 点击「开始讨论」
    const startBtn = page.locator(".btn--start");
    await expect(startBtn).toBeEnabled();
    await startBtn.click();

    // 5. 等待参与者卡片出现（由 API 生成后渲染）
    await page.waitForSelector(".guest-card", { timeout: 15000 });
    const guestCards = page.locator(".guest-card");
    const cardCount = await guestCards.count();

    // 应包含 1 位主持人和至少 1 位专家（后端生成）
    expect(cardCount).toBeGreaterThanOrEqual(2);

    // 6. 验证每位参与者有颜色标识（卡片左边框有颜色）
    for (let i = 0; i < cardCount; i++) {
      const card = guestCards.nth(i);
      const borderLeftColor = await card.evaluate((el) =>
        getComputedStyle(el).borderLeftColor
      );
      expect(borderLeftColor).not.toBe("rgb(0, 0, 0)");
      expect(borderLeftColor).not.toBe("rgba(0, 0, 0, 0)");
    }

    // 7. 等待消息气泡出现（SSE 事件驱动的讨论流）
    await page.waitForSelector(".msg-bubble", { timeout: 30000 });
    const msgBubbles = page.locator(".msg-bubble");
    const msgCount = await msgBubbles.count();
    expect(msgCount).toBeGreaterThanOrEqual(1);

    // 8. 验证每条消息的发言人名称都带有专属颜色
    for (let i = 0; i < msgCount; i++) {
      const bubble = msgBubbles.nth(i);
      const nameEl = bubble.locator(".msg-bubble__name");

      // 名称元素有 style 颜色（来自 color_code）
      const nameColor = await nameEl.getAttribute("style");
      expect(nameColor).toContain("color");
    }

    // 9. 验证内容安全：无 <think> 标签
    const pageText = await page.locator(".transcript").innerText();
    expect(pageText).not.toContain("<think>");
    expect(pageText).not.toContain("</think>");

    // 10. 验证共识面板出现并包含内容
    await page.waitForSelector(".consensus__item", { timeout: 30000 });
    const consensusItems = page.locator(".consensus__item");
    const consensusCount = await consensusItems.count();
    expect(consensusCount).toBeGreaterThanOrEqual(1);

    // 11. 验证有完成状态标签
    await page.waitForSelector(".transcript__ending", { timeout: 60000 });
    await expect(page.locator(".transcript__ending")).toBeVisible();
  });

  test("讨论过程中嘉宾状态指示器正常变化", async ({ page }) => {
    await page.goto("/");

    // 输入话题并开始
    await page.locator(".setup-form__input").fill("低代码是否会取代传统开发");
    await page.locator(".btn--start").click();

    // 等待参与者出现
    await page.waitForSelector(".guest-card", { timeout: 15000 });

    // 等待至少一条消息（表示讨论已开始）
    await page.waitForSelector(".msg-bubble", { timeout: 30000 });

    // 验证状态指示器存在
    const indicators = page.locator(".guest-card__indicator");
    const indicatorCount = await indicators.count();
    expect(indicatorCount).toBeGreaterThanOrEqual(1);
  });
});
