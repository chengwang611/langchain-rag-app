

def dfs(i,nums,choices) :
    if i ==len(nums) :
        if len(choices) ==3 :
            print(choices)
        return
    choices.append(nums[i])
    dfs(i+1,nums,choices)
    choices.pop()
    dfs(i+1,nums,choices)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("Running sample ingestion and review process...")
    nums =[1,2,3,4,5,6,7,8,9]
    for i in range(1,4):
        print(i)
    choices = []
    dfs(0,nums,choices)

if __name__ == "__main__":
    main()
