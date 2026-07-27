#include <gtest/gtest.h>
#include "StringUtils.h"

TEST(LowerTest, Uppercase)
{
    EXPECT_EQ(lower("HELLO"), "hello");
}

TEST(LowerTest, MixedCase)
{
    EXPECT_EQ(lower("HeLlO"), "hello");
}

TEST(LowerTest, EmptyString)
{
    EXPECT_EQ(lower(""), "");
}

TEST(LowerTest, NumbersUnaffected)
{
    EXPECT_EQ(lower("ABC123"), "abc123");
}