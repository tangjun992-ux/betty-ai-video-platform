"""
KIE Adapter Direct Test — Image + Video Generation
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ["KIE_API_KEY"] = "e56cda27611a71ad0ad6548733a9192f"

from app.adapters.kie_adapter import KieAdapter


async def test_image():
    print("\n" + "=" * 60)
    print("TEST 1: Image → gpt-image-2")
    print("=" * 60)
    adapter = KieAdapter()
    print(f"  Provider: {adapter.provider_name} | URL: {adapter._base_url}")
    try:
        result = await adapter.generate_image(
            prompt="一只可爱的橘猫趴在窗台上晒太阳",
            model_id="gpt-image-2",
            size="1024x1024",
        )
        print(f"  ✅ SUCCESS! URL: {result.media_url[:80]}...")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


async def test_video():
    print("\n" + "=" * 60)
    print("TEST 2: Video → seedance-2.0-fast")
    print("=" * 60)
    adapter = KieAdapter()
    try:
        result = await adapter.generate_video(
            prompt="A serene lake at sunset with gentle ripples",
            model_id="seedance-2.0-fast",
            duration=5,
            resolution="1080p",
        )
        print(f"  ✅ SUCCESS! URL: {result.media_url[:80]}...")
        return True
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False


async def main():
    print("=" * 60)
    print(" KIE ADAPTER TEST SUITE")
    print("=" * 60)

    img_ok = await test_image()
    vid_ok = await test_video()

    print("\n" + "=" * 60)
    print(f" RESULTS: Image={'✅' if img_ok else '❌'}  Video={'✅' if vid_ok else '❌'}")
    print("=" * 60)
    sys.exit(0 if (img_ok and vid_ok) else 1)


if __name__ == "__main__":
    asyncio.run(main())
