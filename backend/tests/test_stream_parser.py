"""流式 JSON 解析器与代码块清洗器单元测试。

验证 JsonStreamParser 和 clean_code_blocks 在
残缺、跨 chunk、带 markdown 包装等边缘情况下的鲁棒性。
"""

from app.services.llm_service import JsonStreamParser, clean_code_blocks


# ============================================================
# clean_code_blocks 测试
# ============================================================

class TestCodeBlockCleaner:
    """验证代码块标记清洗器不会让系统崩溃。"""

    def test_clean_simple_json_tag(self):
        """移除 ```json 前导标记。"""
        result = clean_code_blocks('```json\n{"speak": "hello"}\n```')
        assert result == '{"speak": "hello"}'

    def test_clean_triple_backtick(self):
        """移除 ``` 包裹标记。"""
        result = clean_code_blocks('```\n{"thought": "ok"}\n```')
        assert result == '{"thought": "ok"}'

    def test_clean_no_block_no_change(self):
        """没有代码块标记的文本保持不变。"""
        result = clean_code_blocks('{"speak": "hello"}')
        assert result == '{"speak": "hello"}'

    def test_clean_tilde_block(self):
        """处理 ~~~ 波浪线代码块。"""
        result = clean_code_blocks('~~~json\n{"speak": "test"}\n~~~')
        assert result == '{"speak": "test"}'

    def test_clean_partial_block(self):
        """处理只有开标签没有闭标签的残缺情况。"""
        result = clean_code_blocks('```json\n{"speak": "hello"}')
        assert result == '{"speak": "hello"}'

    def test_clean_empty_string(self):
        """空字符串不崩溃。"""
        result = clean_code_blocks("")
        assert result == ""


# ============================================================
# JsonStreamParser 测试
# ============================================================

class TestJsonStreamParser:
    """验证解析器能处理各种边缘情况。"""

    def test_single_complete_json(self):
        """单个完整 JSON 对象。"""
        parser = JsonStreamParser()
        results = parser.feed('{"thought": "hmm", "speak": "hello"}')
        assert len(results) == 1
        assert results[0]["thought"] == "hmm"
        assert results[0]["speak"] == "hello"

    def test_chunk_split_across_boundary(self):
        """JSON 对象被截断在两个 chunk 之间。"""
        parser = JsonStreamParser()
        r1 = parser.feed('{"thought": "hmm", "speak": "hel')
        assert len(r1) == 0  # 还不完整

        r2 = parser.feed('lo"}')
        assert len(r2) == 1
        assert r2[0]["speak"] == "hello"

    def test_brace_split_across_chunks(self):
        """花括号本身被截断在 chunk 边界。"""
        parser = JsonStreamParser()
        r1 = parser.feed('{"thought": "思考中", "speak": "发言')
        assert len(r1) == 0

        r2 = parser.feed('内容"}')
        assert len(r2) == 1
        assert r2[0]["speak"] == "发言内容"

    def test_multiple_objects_in_single_chunk(self):
        """单个 chunk 包含多个 JSON 对象（逐个流式吐出）。"""
        parser = JsonStreamParser()
        results = parser.feed(
            '{"thought":"a"}{"thought":"b","speak":"c"}'
        )
        assert len(results) == 2
        assert results[0]["thought"] == "a"
        assert results[1]["speak"] == "c"

    def test_corrupted_json_skipped_gracefully(self):
        """损坏的 JSON 被静默跳过，不抛异常。"""
        parser = JsonStreamParser()
        results = parser.feed('{bad json}')
        assert len(results) == 0

    def test_mixed_good_and_bad_json(self):
        """好 JSON 和坏 JSON 混在一起，坏的被跳过。"""
        parser = JsonStreamParser()
        results = parser.feed('{"speak":"ok"}{broken}{"speak":"also ok"}')
        assert len(results) == 2
        assert results[0]["speak"] == "ok"
        assert results[1]["speak"] == "also ok"

    def test_code_block_stripped_before_parse(self):
        """parse 前自动清洗 markdown 代码块。"""
        parser = JsonStreamParser()
        results = parser.feed('```json\n{"speak": "hello"}\n```')
        assert len(results) == 1
        assert results[0]["speak"] == "hello"

    def test_multiple_objects_in_separate_chunks(self):
        """多个 JSON 对象跨多个 chunk 逐个流出。"""
        parser = JsonStreamParser()
        r1 = parser.feed('{"thought": "thinking..."}')
        assert len(r1) == 1
        assert r1[0]["thought"] == "thinking..."

        r2 = parser.feed('{"speak": "speaking now"}')
        assert len(r2) == 1
        assert r2[0]["speak"] == "speaking now"

    def test_flush_returns_none(self):
        """flush 返回 None，无 pending 数据。"""
        parser = JsonStreamParser()
        parser.feed('{"thought": "done"}')
        assert parser.flush() is None

    def test_deeply_nested_braces(self):
        """处理文本内包含花括号的情况。"""
        parser = JsonStreamParser()
        text = '{"speak": "A {特殊} 情况 {测试}"}'
        results = parser.feed(text)
        assert len(results) == 1
        assert "{特殊}" in results[0]["speak"]