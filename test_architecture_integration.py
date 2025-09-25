# test_architecture_integration.py
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# テスト対象のモジュールをインポート
from lm_studio_rag.storage import RAGStorage
from architecture.concrete_understanding.base import ConcreteUnderstanding
from architecture.concrete_understanding.schema_architecture import EpisodeData
from architecture.user_response.generator import UserResponseGenerator
from architecture.user_response.schema import UserResponse

class TestArchitectureIntegration(unittest.TestCase):
    """
    abstract_recognition -> concrete_understanding -> user_response の
    一連のフローを検証する統合テスト。
    """

    @patch('lm_studio_rag.lm_studio_client.LMStudioClient')
    def test_full_integration_flow(self, MockLMStudioClient):
        """LMStudioClientをモック化して、アーキテクチャ全体の流れをテストします。"""
        # 1. モックとテストデータの設定
        # -----------------------------------------------------
        mock_lm_client = MockLMStudioClient.return_value
        # generate_responseが呼ばれるたびに、このリストから順に応答を返すように設定
        mock_lm_client.generate_response.side_effect = [
            "公園で犬と遊ぶこと",  # 1. _create_rag_query用
            "楽しい気持ち、少し興奮",    # 2. _run_estimation (感情) 用
            "犬はかわいい、一緒に走りたい", # 3. _run_estimation (思考) 用
            # 4. user_response.generate用 (指定された形式で返す)
            "DECISION: 犬と積極的に関わることを決める\nACTION: 犬に近づいて、飼い主に触っても良いか尋ねる\nRESPONSE: わんちゃん可愛いですね！触っても大丈夫ですか？"
        ]

        # インメモリRAGストレージの準備
        storage = RAGStorage(USE_MEMORY_RUN=True)
        storage.save_experience_data(
            text="昔、近所の犬とよく遊んだ楽しい思い出がある",
            metadata={"source": "test_data"}
        )

        # テスト入力
        field_info_input = "晴れた日の午後、公園で人懐っこいゴールデンレトリバーを見かけた"

        # 2. 実行
        # -----------------------------------------------------

        # Step 1 & 2: ConcreteUnderstandingプロセスを開始し、抽象的理解を取得
        concrete_process = ConcreteUnderstanding(storage=storage, lm_client=mock_lm_client)
        abstract_result = concrete_process.start_inference(field_info_input)

        # Step 3: UserResponseGeneratorへの入力となる具象的理解データ(EpisodeData)を準備
        # (このテストの関心はモジュール間連携のため、手動で作成します)
        concrete_info = EpisodeData(
            episode_id="ep1",
            thread_id="th1",
            timestamp=datetime.now(),
            sequence_in_thread=1,
            source_type="user_input",
            author="user",
            content_type="storytelling_personal_event",
            text_content=field_info_input,
            status="active",
            sensitivity_level="medium"
        )

        # Step 4: UserResponseGeneratorプロセスを実行
        response_gen = UserResponseGenerator(lm_client=mock_lm_client)
        final_response: UserResponse = response_gen.generate(
            abstract_info=abstract_result,
            concrete_info=concrete_info,
            field_info=field_info_input
        )
        print(final_response.final_response)

        # 3. 検証
        # -----------------------------------------------------

        # abstract_resultの検証
        self.assertIsNotNone(abstract_result, "抽象的理解の結果が生成されていません")
        self.assertEqual(abstract_result.emotion_estimation, "楽しい気持ち、少し興奮")
        self.assertEqual(abstract_result.think_estimation, "犬はかわいい、一緒に走りたい")

        # final_responseの検証
        self.assertIsInstance(final_response, UserResponse, "最終応答がUserResponseクラスのインスタンスではありません")
        self.assertEqual(final_response.inferred_decision, "犬と積極的に関わることを決める")
        self.assertEqual(final_response.inferred_action, "犬に近づいて、飼い主に触っても良いか尋ねる")
        self.assertEqual(final_response.final_response, "わんちゃん可愛いですね！触っても大丈夫ですか？")

        # モックが期待通りに呼び出されたか確認
        self.assertEqual(mock_lm_client.generate_response.call_count, 4, "LMClientの呼び出し回数が想定と異なります")

if __name__ == '__main__':
    unittest.main()
