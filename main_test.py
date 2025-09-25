# main.py
"""
Example workflow:
 1. Load sample texts
 2. Classify each text (hybrid classifier)
 3. Save into vector DB by category with metadata
 4. Run a sample RAG query (search + LLM generation)
"""
from lm_studio_rag.config import LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY
from lm_studio_rag.lm_studio_client import LMStudioClient
from lm_studio_rag.classifier import ContentClassifier
from lm_studio_rag.storage import RAGStorage
from lm_studio_rag.utils import now_iso
import os
# import architecture.abstract_recognitio.base as arh_abstract
from architecture.abstract_recognition import base as arh_abstract
from architecture.concrete_understanding.base import ConcreteUnderstanding


# データ作成について
## sample data
PERSONALITY_SAMPLES = [
    "私は内向的な性格で、静かな環境を好みます",
    "コーヒーよりも紅茶派です",
    "数学が得意で論理的思考を重視します"
]
EXPERIENCE_SAMPLES = [
    "昨日、新しいレストランに行きました",
    "大学時代にプログラミングを学んだ経験があります",
    "先月の出張で面白い発見をしました"
]

def build_and_run():
    # 1) initialize classifier (no LLM)
    classifier = ContentClassifier(use_llm=False)
    # train small classifier on provided samples for better accuracy
    classifier.train_small_classifier({
        "personality": PERSONALITY_SAMPLES,
        "experience": EXPERIENCE_SAMPLES
    })

    # 2) initialize storage
    storage = RAGStorage(USE_MEMORY_RUN=True)

    # 3) ingest some mixed items
    mixed_items = [

    ]
    for t in mixed_items:
        res = classifier.classify(t)
        print("Classify:", t, "->", res)
        metadata = {"classifier": res, "source": "user_upload", "saved_at": now_iso()}
        if res["label"] == "personality":
            storage.save_personality_data(t, metadata)
        else:
            storage.save_experience_data(t, metadata)

    
    def answer_run():
        # if input_text == "test":
        feild_info_input:str = """
{
  "field_info": {
    "field_env": {
      "time": "evening",
      "weather": "cloudy",
      "location": "abandoned warehouse district"
    },
    "human_env": [
      {
        "nam": "Kenji Tanaka",
        "feel": "seems cautious and alert",
        "state": "partially hidden behind a container"
      },
      {
        "nam": "Yumi Sato",
        "feel": "appears anxious",
        "state": "clutching a small bag tightly"
      },
      {
        "nam": "Goro Suzuki",
        "feel": "has a determined look",
        "state": "standing in the open, slightly wounded"
      },
      {
        "nam": "Masaru Honda",
        "feel": "looks calm but is observing everything",
        "state": "leaning against a wall, arms crossed"
      },
      {
        "nam": "Unknown Person",
        "feel": "unreadable emotion",
        "state": "watching from the shadows of a building"
      }
    ]
  }
}
        """
        output_code = arh_abstract.architecture_base(storage=storage,field_info_input=feild_info_input)
        print(f"RAG:->{output_code.emotion_estimation}\nGAR:{output_code.think_estimation}")
    answer_run()

def test_thought_experiment():
    """
    Tests the thought experiment flow.
    """
    print("\n--- Running Thought Experiment Test ---")
    
    # 1. Initialize storage and the understanding process
    storage = RAGStorage(USE_MEMORY_RUN=True)
    understanding_process = ConcreteUnderstanding(storage)
    
    # 2. Define dummy user inputs for the test
    scenario_id = "THOUGHT_EXP_001"
    direct_answer = "スイッチを切り替える"
    real_experience = "昔、多数決で友人の意見を押し切ってしまったことがある。後で少し後悔した。"
    
    # 3. Run the thought experiment
    thought_episode, experience_episode = understanding_process.start_thought_experiment(
        scenario_id=scenario_id,
        user_direct_answer=direct_answer,
        user_real_experience=real_experience
    )
    
    # 4. Assertions to verify the results
    print("Verifying results...")
    
    # Check that both episodes were created
    assert thought_episode is not None, "Thought episode should be created"
    assert experience_episode is not None, "Experience episode should be created"
    
    # Check content types
    assert thought_episode.content_type == "value_articulation", f"Incorrect content_type for thought_episode: {thought_episode.content_type}"
    assert experience_episode.content_type == "storytelling_personal_event", f"Incorrect content_type for experience_episode: {experience_episode.content_type}"
    
    # Check text content
    assert thought_episode.text_content == direct_answer
    assert experience_episode.text_content == real_experience
    
    # Check the link between episodes
    assert experience_episode.related_episode_ids is not None, "Experience episode should be related to the thought episode"
    assert len(experience_episode.related_episode_ids) == 1, "There should be one related episode"
    assert experience_episode.related_episode_ids[0].episode_id == thought_episode.episode_id, "The related ID does not match"
    assert experience_episode.related_episode_ids[0].relationship_type == "is_response_to"

    print("All assertions passed!")
    print("--- Thought Experiment Test Finished ---\n")

from architecture.response_generation.response_generator import ResponseGenerator
from architecture.response_generation.schema_response import UserResponse

def test_response_generation():
    """
    Tests the end-to-end user response generation process.
    """
    print("\n--- Running User Response Generation Test ---")

    # 1. Initialize storage and LMStudioClient
    storage = RAGStorage(USE_MEMORY_RUN=True)
    lm_client = LMStudioClient() # Assuming LMStudioClient can be initialized without specific API keys for testing

    # 2. Instantiate ResponseGenerator
    response_generator = ResponseGenerator(storage, lm_client)

    # 3. Provide a sample field_info_input
    field_info_input = """
{
  "field_info": {
    "field_env": {
      "time": "morning",
      "weather": "sunny",
      "location": "park"
    },
    "human_env": [
      {
        "nam": "Child A",
        "feel": "happy",
        "state": "playing on swings"
      },
      {
        "nam": "Parent B",
        "feel": "relaxed",
        "state": "watching Child A"
      }
    ]
  }
}
    """

    # 4. Generate user response
    user_response: Optional[UserResponse] = response_generator.generate_user_response(field_info_input)

    # 5. Assertions to verify the results
    print("Verifying results...")

    assert user_response is not None, "UserResponse should be generated"
    assert isinstance(user_response, UserResponse), "Returned object should be an instance of UserResponse"
    assert user_response.abstract_understanding is not None, "Abstract understanding should be populated"
    assert user_response.abstract_understanding.emotion_estimation is not None, "Emotion estimation should be populated"
    assert user_response.abstract_understanding.think_estimation is not None, "Think estimation should be populated"
    assert user_response.concrete_understanding_summary is not None, "Concrete understanding summary should be populated"
    assert user_response.inferred_decision is not None, "Inferred decision should be populated"
    assert user_response.inferred_action is not None, "Inferred action should be populated"
    assert user_response.generated_response_text is not None, "Generated response text should be populated"

    print("Abstract Understanding (Emotion):", user_response.abstract_understanding.emotion_estimation)
    print("Abstract Understanding (Thought):", user_response.abstract_understanding.think_estimation)
    print("Concrete Understanding Summary:", user_response.concrete_understanding_summary)
    print("Inferred Decision:", user_response.inferred_decision)
    print("Inferred Action:", user_response.inferred_action)
    print("Generated Response Text:", user_response.generated_response_text)

    print("All assertions passed for user response generation!")
    print("--- User Response Generation Test Finished ---\n")


if __name__ == "__main__":
    # build_and_run()
    test_thought_experiment()
    test_response_generation()